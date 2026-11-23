#!/usr/bin/env python3
"""Run cases x configs x repetitions with resume, retry, and manifest provenance (Tier 4 - C14)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.model import ModelConfig
from provguard.schemas import EquivalenceMode
from provguard.sinks import SinkClassifier
from provguard.trials import load_cases, run_trial_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="cases", help="directory of JSON cases or single file")
    parser.add_argument(
        "--configs",
        default="B0,labels,gate,full",
        help="comma-separated list of configurations (e.g. B0,labels,gate,full)",
    )
    parser.add_argument("--reps", type=int, default=5, help="repetitions per (case, config)")
    parser.add_argument("--out", default="results", help="output directory for trials.jsonl")
    parser.add_argument("--run-id", default=None, help="explicit run_id")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--provider",
        default="heuristic",
        choices=("heuristic", "gemini", "openai", "ollama"),
    )
    parser.add_argument("--model", default="heuristic-v1")
    parser.add_argument("--trials", "-k", type=int, default=5, help="Causal Gate re-execution k")
    parser.add_argument("--threshold", "--theta", type=float, default=0.5)
    parser.add_argument(
        "--equivalence",
        default="control",
        choices=("control", "strict"),
    )
    parser.add_argument("--sinks", default=None, help="optional sinks.yaml path")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--no-resume", action="store_true", help="overwrite instead of resuming")
    parser.add_argument("--freeze", action="store_true", help="mark manifest as frozen")
    args = parser.parse_args(argv)

    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    if not configs:
        print("error: --configs cannot be empty", file=sys.stderr)
        return 2

    try:
        cases = load_cases(args.cases, auto_generate_if_empty=True)
        classifier = SinkClassifier.from_yaml(args.sinks) if args.sinks else SinkClassifier()
        summary = run_trial_matrix(
            cases=cases,
            configs=configs,
            reps=args.reps,
            out_dir=args.out,
            run_id=args.run_id,
            seed=args.seed,
            model_config=ModelConfig(
                provider=args.provider,
                model_name=args.model,
                temperature=0.0,
                seed=args.seed,
            ),
            classifier=classifier,
            gate_trials=args.trials,
            gate_threshold=args.threshold,
            equivalence=EquivalenceMode(args.equivalence),
            max_retries=args.max_retries,
            resume=not args.no_resume,
            freeze=args.freeze,
        )
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
