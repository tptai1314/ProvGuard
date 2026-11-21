#!/usr/bin/env python3
"""Reproduce the analytical computations behind paper Table 5 and Figure 7."""

from __future__ import annotations

import argparse
import json

from provguard.statistics import exact_minimum_trials, hoeffding_trials


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q0", type=float, default=0.2)
    parser.add_argument("--q1", type=float, default=0.8)
    parser.add_argument("--theta", type=float, default=0.5)
    parser.add_argument("--delta", type=float, default=0.01)
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "result_kind": "analytical calculation, not an experimental result",
                "exact_minimum_trials": exact_minimum_trials(
                    args.q0, args.q1, args.theta, args.delta
                ),
                "hoeffding_sufficient_trials": hoeffding_trials(
                    args.q0, args.q1, args.theta, args.delta
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

