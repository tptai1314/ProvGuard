#!/usr/bin/env python3
"""Generate LaTeX result tables (tab_asr.tex, tab_utility.tex) from trials.jsonl (Tier 7 - C22, C24)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.reporting import generate_tables


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", default="results/trials.jsonl", help="path to trials.jsonl")
    parser.add_argument("--out", default="results/tables", help="output directory for .tex tables")
    parser.add_argument(
        "--sections-out",
        default="sections/results",
        help="also write tab_asr.tex and tab_utility.tex into sections/results/ (empty to skip)",
    )
    args = parser.parse_args(argv)

    try:
        sec_dir = args.sections_out if args.sections_out else None
        summary = generate_tables(args.trials, args.out, sections_dir=sec_dir)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
