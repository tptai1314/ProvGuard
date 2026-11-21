from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.datasets import JsonlTrialAdapter
from ..config import ExperimentConfig
from ..io import write_json, write_jsonl
from ..metrics import attack_success_rates, false_block_rate, sink_coverage, task_success_rate
from ..statistics import exact_minimum_trials, hoeffding_trials
from ..synthetic import SYNTHETIC_NOTICE, run_synthetic_trials


def calibrate(config: ExperimentConfig, output_dir: str | Path) -> dict[str, Any]:
    theta = config.gate.threshold
    result = {
        "result_kind": "analytical calculation, not an experimental result",
        "q0": config.q0,
        "q1": config.q1,
        "theta": theta,
        "delta": config.delta,
        "exact_minimum_trials": exact_minimum_trials(
            config.q0, config.q1, theta, config.delta
        ),
        "hoeffding_sufficient_trials": hoeffding_trials(
            config.q0, config.q1, theta, config.delta
        ),
    }
    write_json(Path(output_dir) / "calibration.json", result)
    return result


def summarize(rows: list[dict]) -> dict[str, Any]:
    return {
        "result_kind": SYNTHETIC_NOTICE,
        "attack_success_rate_by_channel": attack_success_rates(rows),
        "false_block_rate": false_block_rate(rows),
        "task_success_rate": task_success_rate(rows),
        "sink_coverage": sink_coverage(rows),
        "trial_count": len(rows),
    }


def evaluate(config: ExperimentConfig, output_dir: str | Path) -> dict[str, Any]:
    if config.mode == "synthetic":
        rows = run_synthetic_trials(
            seed=config.seed,
            repetitions=config.repetitions,
            trials=config.gate.trials,
            threshold=config.gate.threshold,
            equivalence=config.gate.equivalence,
        )
    else:
        if not config.data_root:
            raise ValueError("Real mode requires data.root with a manually provisioned trials.jsonl")
        rows = JsonlTrialAdapter().load(config.data_root)
        required = {
            "protected",
            "gate_decision",
            "dispatch_status",
            "adversarial_success",
            "task_completed",
        }
        for index, row in enumerate(rows, 1):
            missing = required - row.keys()
            if missing:
                raise ValueError(f"normalized real record {index} missing {sorted(missing)}")
    output = Path(output_dir)
    write_jsonl(output / "trials.jsonl", rows)
    result = summarize(rows)
    if config.mode == "real":
        result["result_kind"] = "real normalized logs supplied by user; provenance must be audited"
    write_json(output / "results.json", result)
    return result


def ablate(config: ExperimentConfig, output_dir: str | Path) -> dict[str, Any]:
    variants = {
        "B0-no-defense": {"gate_enabled": False, "binder_enabled": False},
        "PG-L-labels-only": {"gate_enabled": False, "binder_enabled": False},
        "PG-G-gate-only": {"gate_enabled": True, "binder_enabled": False},
        "PG-B-binding-only": {"gate_enabled": False, "binder_enabled": True},
        "PG-minus-perceivability": {
            "gate_enabled": True,
            "binder_enabled": True,
            "disable_perceivability": True,
        },
        "PG-full": {"gate_enabled": True, "binder_enabled": True},
    }
    summaries: dict[str, Any] = {}
    for name, options in variants.items():
        rows = run_synthetic_trials(
            seed=config.seed,
            repetitions=config.repetitions,
            trials=config.gate.trials,
            threshold=config.gate.threshold,
            equivalence=config.gate.equivalence,
            **options,
        )
        summaries[name] = summarize(rows)
    result = {"result_kind": SYNTHETIC_NOTICE, "variants": summaries}
    write_json(Path(output_dir) / "ablation.json", result)
    return result
