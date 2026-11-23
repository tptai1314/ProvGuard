#!/usr/bin/env python3
"""QA check trial runs for missing fields, duplicate trial_ids, and SHA-256 integrity (Tier 4 - C16)."""

from __future__ import annotations

import argparse
import json

from provguard.trials import check_run_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="results", help="run directory or trials.jsonl path")
    parser.add_argument("--expected-trials", type=int, default=None)
    parser.add_argument("--no-manifest", action="store_true", help="do not require manifest.json")
    parser.add_argument("--require-frozen", action="store_true", help="require manifest frozen=true")
    args = parser.parse_args(argv)

    report = check_run_directory(
        args.run_dir,
        expected_trials=args.expected_trials,
        require_manifest=not args.no_manifest,
        require_frozen=args.require_frozen,
    )
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
