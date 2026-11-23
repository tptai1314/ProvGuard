#!/usr/bin/env python3
"""Create, refresh, or freeze manifest.json provenance for a trial run directory (Tier 4 - C15)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provguard.io import write_json
from provguard.model import ModelConfig
from provguard.trials import build_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="results", help="directory containing trials.jsonl")
    parser.add_argument("--run-id", default=None, help="explicit run_id override")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--provider", default="heuristic")
    parser.add_argument("--model", default="heuristic-v1")
    parser.add_argument("--trials", "-k", type=int, default=5)
    parser.add_argument("--threshold", "--theta", type=float, default=0.5)
    parser.add_argument("--freeze", action="store_true", help="lock and freeze the dataset hash")
    parser.add_argument("--out", default=None, help="optional output path for manifest.json")
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    try:
        manifest = build_manifest(
            run_dir=run_dir,
            run_id=args.run_id,
            seed=args.seed,
            model_config=ModelConfig(provider=args.provider, model_name=args.model),
            gate_trials=args.trials,
            gate_threshold=args.threshold,
            frozen=args.freeze,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out) if args.out else run_dir / "manifest.json"
    write_json(out_path, manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
