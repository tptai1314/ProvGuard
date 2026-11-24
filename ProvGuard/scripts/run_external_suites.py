#!/usr/bin/env python3
"""Run ProvGuard evaluation on the 4 downloaded external benchmarks from paper Table 6."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from provguard.adapters.external_suites import (
    load_agenthazard_cases,
    load_androidworld_benign_cases,
    load_ghostei_cases,
    load_not_an_a11y_cases,
)
from provguard.model import ModelConfig
from provguard.reporting import generate_figures, generate_tables
from provguard.schemas import EquivalenceMode
from provguard.trials import check_run_directory, run_trial_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="heuristic", choices=("heuristic", "gemini", "openai", "ollama"))
    parser.add_argument("--model", default="heuristic-v1")
    parser.add_argument("--out", default="results_external_benchmarks")
    parser.add_argument("--ah-limit", type=int, default=24)
    parser.add_argument("--ghostei-per-channel", type=int, default=10)
    parser.add_argument("--aw-limit", type=int, default=20)
    parser.add_argument("--trials", "-k", type=int, default=1)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args(argv)

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    m_cfg = ModelConfig(
        provider=args.provider,
        model_name=args.model,
        temperature=0.0,
        seed=args.seed,
    )

    summaries: dict[str, Any] = {}
    all_rows: list[dict[str, Any]] = []

    # 1. AgentHazard (G1 default app-clearance vs strict third-party-labeled)
    ah_default = load_agenthazard_cases(limit=args.ah_limit, third_party_as_sdk=False)
    ah_strict = load_agenthazard_cases(limit=args.ah_limit, third_party_as_sdk=True)
    # Tag strict cases separately so trial_ids stay distinct
    ah_strict_renamed = [
        type(c)(
            case_id=f"{c.case_id}_strict",
            suite=c.suite,
            channel="sdk_third_party",
            trial_type=c.trial_type,
            task=c.task,
            observation=c.observation,
            attacker_target_id=c.attacker_target_id,
            benign_target_id=c.benign_target_id,
            ground_truth_protected=c.ground_truth_protected,
            metadata=c.metadata,
        )
        for c in ah_strict
    ]
    ah_dir = out_root / "AgentHazard"
    summaries["AgentHazard_default_G1"] = run_trial_matrix(
        cases=ah_default,
        configs=["B0", "labels", "full"],
        reps=1,
        out_dir=ah_dir / "default_g1",
        run_id="ext_agenthazard_g1",
        seed=args.seed,
        model_config=m_cfg,
        gate_trials=args.trials,
        equivalence=EquivalenceMode.CONTROL,
        freeze=args.freeze,
    )
    summaries["AgentHazard_thirdparty_labeled"] = run_trial_matrix(
        cases=ah_strict_renamed,
        configs=["full"],
        reps=1,
        out_dir=ah_dir / "strict_labeled",
        run_id="ext_agenthazard_strict",
        seed=args.seed,
        model_config=m_cfg,
        gate_trials=args.trials,
        equivalence=EquivalenceMode.CONTROL,
        freeze=args.freeze,
    )

    # 2. GhostEI-Bench (Overlay Attack, Popup SMS, Non-script)
    ghost_cases = load_ghostei_cases(per_channel_limit=args.ghostei_per_channel)
    summaries["GhostEI_Bench"] = run_trial_matrix(
        cases=ghost_cases,
        configs=["B0", "labels", "gate", "full"],
        reps=1,
        out_dir=out_root / "GhostEI_Bench",
        run_id="ext_ghostei",
        seed=args.seed,
        model_config=m_cfg,
        gate_trials=args.trials,
        equivalence=EquivalenceMode.CONTROL,
        freeze=args.freeze,
    )

    # 3. Not-An-A11y (Notification, Overlay/WebView, AppCard)
    na_cases = load_not_an_a11y_cases()
    summaries["Not_An_A11y"] = run_trial_matrix(
        cases=na_cases,
        configs=["B0", "labels", "gate", "full"],
        reps=1,
        out_dir=out_root / "Not_An_A11y",
        run_id="ext_not_an_a11y",
        seed=args.seed,
        model_config=m_cfg,
        gate_trials=args.trials,
        equivalence=EquivalenceMode.CONTROL,
        freeze=args.freeze,
    )

    # 4. AndroidWorld (Benign utility TSR & FBR)
    aw_cases = load_androidworld_benign_cases(limit=args.aw_limit)
    summaries["AndroidWorld"] = run_trial_matrix(
        cases=aw_cases,
        configs=["B0", "full"],
        reps=1,
        out_dir=out_root / "AndroidWorld",
        run_id="ext_androidworld",
        seed=args.seed,
        model_config=m_cfg,
        gate_trials=args.trials,
        equivalence=EquivalenceMode.CONTROL,
        freeze=args.freeze,
    )

    # Generate suite-level tables for GhostEI, Not-An-A11y, and combined external attacks
    for sub in ("GhostEI_Bench", "Not_An_A11y", "AndroidWorld"):
        sub_dir = out_root / sub
        generate_tables(sub_dir / "trials.jsonl", sub_dir / "tables")
        check_run_directory(sub_dir, require_frozen=args.freeze)

    for jsonl in (
        ah_dir / "default_g1" / "trials.jsonl",
        out_root / "GhostEI_Bench" / "trials.jsonl",
        out_root / "Not_An_A11y" / "trials.jsonl",
        out_root / "AndroidWorld" / "trials.jsonl",
    ):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                all_rows.append(json.loads(line))

    combined_jsonl = out_root / "combined_trials.jsonl"
    combined_jsonl.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in all_rows) + "\n",
        encoding="utf-8",
    )
    summaries["combined_tables"] = generate_tables(
        combined_jsonl, out_root / "tables"
    )
    summaries["combined_figures"] = generate_figures(
        combined_jsonl, out_root / "figures"
    )

    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
