"""Tests verifying loaders for the 4 downloaded external benchmarks (Table 6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from provguard.adapters.external_suites import (
    generate_adaptive_cases,
    load_agenthazard_cases,
    load_androidlab_benign_cases,
    load_androidworld_benign_cases,
    load_ghostei_cases,
    load_not_an_a11y_cases,
)
from provguard.lattice import IntegrityLabel
from provguard.trials import run_trial_matrix

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_ROOT = REPO_ROOT / "datasets_external"


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "AgentHazard" / "data" / "data" / "static").exists(),
    reason="AgentHazard dataset not provisioned locally",
)
def test_load_agenthazard_cases_supports_g1_and_strict() -> None:
    g1_cases = load_agenthazard_cases(
        EXTERNAL_ROOT / "AgentHazard" / "data" / "data" / "static",
        limit=6,
        third_party_as_sdk=False,
    )
    strict_cases = load_agenthazard_cases(
        EXTERNAL_ROOT / "AgentHazard" / "data" / "data" / "static",
        limit=6,
        third_party_as_sdk=True,
    )
    assert len(g1_cases) == 6
    assert len(strict_cases) == 6
    assert all(c.suite == "AgentHazard" for c in g1_cases)
    assert any(r.label == IntegrityLabel.SDK for r in strict_cases[0].observation.regions)


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "Ghost-EI" / "datasets" / "GhostEI.jsonl").exists(),
    reason="GhostEI dataset not provisioned locally",
)
def test_load_ghostei_cases_stratified() -> None:
    cases = load_ghostei_cases(
        EXTERNAL_ROOT / "Ghost-EI" / "datasets" / "GhostEI.jsonl",
        per_channel_limit=5,
    )
    assert len(cases) == 15
    assert {c.channel for c in cases} == {
        "ghostei_overlay",
        "ghostei_popup_sms",
        "ghostei_non_script",
    }


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "Not-An-A11y" / "Runtime Injection").exists(),
    reason="Not-An-A11y dataset not provisioned locally",
)
def test_load_not_an_a11y_cases() -> None:
    cases = load_not_an_a11y_cases(EXTERNAL_ROOT / "Not-An-A11y")
    assert len(cases) >= 8
    assert {c.channel for c in cases} >= {"a1_notification", "a3_a4_overlay_web", "a9_appcard"}


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "android_world" / "android_world" / "task_metadata.json").exists(),
    reason="AndroidWorld metadata not provisioned locally",
)
def test_load_androidworld_benign_cases() -> None:
    cases = load_androidworld_benign_cases(
        EXTERNAL_ROOT / "android_world" / "android_world" / "task_metadata.json",
        limit=12,
    )
    assert len(cases) == 12
    assert all(c.trial_type == "benign" and c.suite == "AndroidWorld" for c in cases)


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "Android-Lab" / "evaluation" / "config").exists(),
    reason="AndroidLab dataset not provisioned locally",
)
def test_load_androidlab_benign_cases() -> None:
    cases = load_androidlab_benign_cases(
        EXTERNAL_ROOT / "Android-Lab" / "evaluation" / "config",
        limit=18,
    )
    assert len(cases) == 18
    assert all(c.trial_type == "benign" and c.suite == "AndroidLab" for c in cases)
    assert len({c.metadata["app"] for c in cases}) >= 6


def test_generate_adaptive_cases_and_run_all_10_configs_and_4_agents(tmp_path: Path) -> None:
    adaptive = generate_adaptive_cases(per_category=2)
    assert len(adaptive) == 6
    assert {c.channel for c in adaptive} == {
        "adaptive_paraphrase",
        "in_app_g1",
        "adaptive_g2_g3",
    }

    # Verify all 10 Table 8 configs run end-to-end
    all_10_configs = [
        "B0",
        "B1",
        "B2",
        "B3",
        "B4",
        "labels",
        "gate",
        "binder",
        "no_perc",
        "full",
    ]
    summary = run_trial_matrix(
        cases=adaptive[:2],
        configs=all_10_configs,
        reps=1,
        out_dir=tmp_path / "all10",
        gate_trials=1,
        freeze=True,
    )
    assert summary["total_trials"] == 20
    assert summary["infra_failures"] == 0

    # Verify all 4 paper agents run through run_trial_matrix
    for agent_key in ("droidrun", "ui-tars", "open-autoglm", "mobile-agent-v3"):
        ag_sum = run_trial_matrix(
            cases=adaptive[:1],
            configs=["B0", "full"],
            reps=1,
            out_dir=tmp_path / f"ag_{agent_key}",
            gate_trials=1,
            agent_name=agent_key,
        )
        assert ag_sum["total_trials"] == 2
        assert ag_sum["infra_failures"] == 0

