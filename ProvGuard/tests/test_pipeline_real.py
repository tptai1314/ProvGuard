"""End-to-end integration tests across Tiers 1-7 (Tier 8 - C25)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from provguard.agent import PromptAgentAdapter
from provguard.benign import build_benign_suite, check_benign_outcome, evaluate_benign_suite
from provguard.binder import DispatchBinder, simulate_live_mutation
from provguard.dispatch import ActionDispatcher
from provguard.gate import CausalGate
from provguard.lattice import IntegrityLabel
from provguard.masking import (
    mask_observation,
    mask_observation_image,
    untrusted_observation_region_ids,
)
from provguard.model import ModelConfig, create_model_client
from provguard.notifications import parse_notification_dump
from provguard.observation import (
    BuildSettings,
    build_observation,
    load_observation,
    observation_to_dict,
)
from provguard.prompt import PromptMode, build_prompt
from provguard.reporting import generate_figures, generate_tables
from provguard.schemas import (
    Action,
    ActionOp,
    DispatchStatus,
    GateDecision,
    SinkClass,
    Transcript,
)
from provguard.sinks import SinkClassifier
from provguard.trials import check_run_directory, generate_default_cases, run_trial_matrix
from provguard.uidump import parse_ui_xml
from provguard.windowdump import display_size_from_dump, parse_window_dump

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "obs_settings"


class _RecordingAdb:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def shell(self, command: str, *, timeout: float | None = None) -> str:
        self.commands.append(command)
        return ""


def test_end_to_end_real_fixture_pipeline(tmp_path: Path) -> None:
    """Smoke test full pipeline: raw Android dumps -> labels -> prompt -> agent -> gate -> binder -> dispatch."""

    # 1. Tier 1: Parse raw ui.xml, windows.txt, notifications.txt into a labelled Observation
    nodes = parse_ui_xml(FIXTURE_DIR / "ui.xml")
    windows_text = (FIXTURE_DIR / "windows.txt").read_text(encoding="utf-8")
    windows = parse_window_dump(windows_text)
    notifs = parse_notification_dump((FIXTURE_DIR / "notifications.txt").read_text(encoding="utf-8"))
    display = display_size_from_dump(windows_text) or (1080, 2400)

    build_res = build_observation(
        observation_id="obs_e2e_settings",
        step=0,
        nodes=nodes,
        windows=windows,
        display=display,
        settings=BuildSettings(target_package="com.android.settings"),
        notifications=notifs,
    )
    labels_file = tmp_path / "labels.json"
    labels_file.write_text(
        json.dumps(observation_to_dict(build_res), indent=2),
        encoding="utf-8",
    )
    observation = load_observation(labels_file)
    assert len(observation.regions) > 0

    # 2. Tier 2: Build prompt, run agent decision, mask observation & image, evaluate Causal Gate
    client = create_model_client(ModelConfig(provider="heuristic", model_name="heuristic-v1"))
    adapter = PromptAgentAdapter(model_client=client, prompt_mode=PromptMode.LABELED)
    transcript = Transcript(task="Open Network & internet settings", observations=(observation,))
    bundle = build_prompt(transcript, mode=PromptMode.LABELED)
    assert "SECURITY POLICY:" in bundle.system_prompt

    proposed = adapter.decide(transcript)
    assert proposed.op == ActionOp.TAP
    assert proposed.target_region_id is not None

    untrusted_ids = untrusted_observation_region_ids(observation, IntegrityLabel.APP)
    masked_obs = mask_observation(observation, untrusted_ids)
    assert len(masked_obs.regions) == len(observation.regions)

    dummy_rgb = np.full((display[1], display[0], 3), 240, dtype=np.uint8)
    masked_rgb, _masked_px = mask_observation_image(
        dummy_rgb, observation, untrusted_ids, tile_size=32
    )
    assert masked_rgb.shape == dummy_rgb.shape

    classifier = SinkClassifier()
    gate = CausalGate(sink_classifier=classifier, trials=3, threshold=0.5)
    classified, gate_result = gate.evaluate(proposed, transcript, adapter.decide)
    assert gate_result.decision == GateDecision.PASS

    # 3. Tier 3: Dispatch Binder verification & ADB command execution
    adb = _RecordingAdb()
    dispatcher = ActionDispatcher(
        binder=DispatchBinder(),
        adb=adb,  # type: ignore[arg-type]
        dry_run=False,
        verify_binding=True,
    )
    exec_rec = dispatcher.execute(classified, observation, live_observation=observation)
    assert exec_rec.status == DispatchStatus.DELIVERED
    assert exec_rec.executed is True
    assert len(adb.commands) == 1
    assert adb.commands[0].startswith("input tap ")

    # Simulate dispatch-time UI rebinding (overlay attack) and verify dispatcher aborts
    adb_rebinding = _RecordingAdb()
    dispatcher_rebind = ActionDispatcher(
        binder=DispatchBinder(),
        adb=adb_rebinding,  # type: ignore[arg-type]
        dry_run=False,
        verify_binding=True,
    )
    mutated_live = simulate_live_mutation(
        observation, "overlay", target_region_id=classified.target_region_id
    )
    rebind_rec = dispatcher_rebind.execute(
        classified, observation, live_observation=mutated_live
    )
    assert rebind_rec.status == DispatchStatus.REOBSERVE
    assert rebind_rec.executed is False
    assert adb_rebinding.commands == []


def test_tier6_benign_20_tasks_and_checker(tmp_path: Path) -> None:
    specs = build_benign_suite(tmp_path / "benign_cases")
    assert len(specs) == 20
    assert sum(1 for s in specs if s.ground_truth_protected) == 12
    assert sum(1 for s in specs if not s.ground_truth_protected) == 8
    assert sum(1 for s in specs if s.has_benign_distractor) == 6

    sink_classes = {s.expected_sink_class for s in specs if s.expected_sink_class is not None}
    assert sink_classes == {
        SinkClass.SEND,
        SinkClass.PAY,
        SinkClass.DELETE,
        SinkClass.SHARE,
        SinkClass.INSTALL,
        SinkClass.GRANT,
    }

    summary = evaluate_benign_suite(specs=specs, configs=["B0", "labels", "gate", "full"])
    for cfg in ("B0", "labels", "gate", "full"):
        cfg_stats = summary["by_config"][cfg]
        assert cfg_stats["task_success_rate"] == 1.0
        assert cfg_stats["false_block_rate"] == 0.0

    # Direct negative check on check_benign_outcome when a protected task is falsely escalated
    first_protected = specs[0]
    false_block_check = check_benign_outcome(
        first_protected,
        Action(
            op=ActionOp.TAP,
            observation_id=first_protected.observation.observation_id,
            target_region_id="r0.2",
        ),
        gate_decision="escalate",
        dispatch_status="dropped",
    )
    assert false_block_check.false_blocked is True
    assert false_block_check.task_completed is False


def test_tier7_make_tables_and_make_figures(tmp_path: Path) -> None:
    all_cases = generate_default_cases()
    subset = (
        [c for c in all_cases if c.channel == "hidden"][:3]
        + [c for c in all_cases if c.channel == "overlay"][:3]
        + [c for c in all_cases if c.channel == "notif"][:3]
        + [c for c in all_cases if c.channel == "rebinding"][:2]
        + [c for c in all_cases if c.trial_type == "benign"][:4]
    )
    run_dir = tmp_path / "run_out"
    run_trial_matrix(
        cases=subset,
        configs=["B0", "labels", "gate", "full"],
        reps=2,
        out_dir=run_dir,
        freeze=True,
    )
    qa = check_run_directory(run_dir, require_frozen=True)
    assert qa.passed is True

    tables_dir = tmp_path / "tables"
    sections_dir = tmp_path / "sections_results"
    tab_summary = generate_tables(
        run_dir / "trials.jsonl",
        tables_dir,
        sections_dir=sections_dir,
    )
    assert tab_summary["total_trials"] == len(subset) * 4 * 2
    assert tab_summary["pooled_asr"]["full"] == 0.0
    assert tab_summary["fbr"]["full"] == 0.0
    assert tab_summary["tsr"]["full"] == 100.0

    tab_asr_tex = (tables_dir / "tab_asr.tex").read_text(encoding="utf-8")
    tab_util_tex = (tables_dir / "tab_utility.tex").read_text(encoding="utf-8")
    assert "\\begin{table}" in tab_asr_tex
    assert "Pooled Attack ASR" in tab_asr_tex
    assert "PG (Full system)" in tab_util_tex
    assert (sections_dir / "tab_asr.tex").exists()
    assert (sections_dir / "tab_utility.tex").exists()

    figs_dir = tmp_path / "figures"
    figs = generate_figures(run_dir / "trials.jsonl", figs_dir)
    assert len(figs) == 6
    for fig_path in figs:
        assert Path(fig_path).exists()
        assert Path(fig_path).stat().st_size > 0
