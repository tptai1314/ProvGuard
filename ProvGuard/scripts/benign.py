#!/usr/bin/env python3
"""Run and check the 20 benign Android GUI tasks across configurations (Tier 6 - C21)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from provguard.benign import build_benign_suite, evaluate_benign_suite
from provguard.io import write_json
from provguard.model import ModelConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", default=None, help="optional directory to export 20 benign JSON cases")
    parser.add_argument("--configs", default="B0,labels,gate,full")
    parser.add_argument("--provider", default="heuristic", choices=("heuristic", "gemini", "openai", "ollama"))
    parser.add_argument("--model", default="heuristic-v1")
    parser.add_argument("--trials", "-k", type=int, default=5)
    parser.add_argument("--threshold", "--theta", type=float, default=0.5)
    parser.add_argument("--out", default=None, help="optional JSON output path")
    args = parser.parse_args(argv)

    specs = build_benign_suite(args.export_dir)
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    summary = evaluate_benign_suite(
        specs=specs,
        configs=configs,
        model_config=ModelConfig(provider=args.provider, model_name=args.model, temperature=0.0),
        gate_trials=args.trials,
        gate_threshold=args.threshold,
    )
    if args.out:
        write_json(Path(args.out), summary)

    printable = {k: v for k, v in summary.items() if k != "records"}
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
