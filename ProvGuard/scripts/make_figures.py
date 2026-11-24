#!/usr/bin/env python3
"""Generate 3 PDF + PNG experimental figures from trials.jsonl (Tier 7 - C23)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.reporting import generate_figures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", default="results/trials.jsonl", help="path to trials.jsonl")
    parser.add_argument("--out", default="results/figures", help="output directory for figures")
    args = parser.parse_args(argv)

    try:
        written = generate_figures(args.trials, args.out)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"figures_written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
