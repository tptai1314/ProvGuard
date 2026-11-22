#!/usr/bin/env python3
"""Render an observation (labels.json) and user task into an agent prompt (Tier 2 - C7)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provguard.observation import load_observation
from provguard.prompt import PromptMode, build_observation_prompt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observation directory or labels.json path")
    parser.add_argument("--task", required=True, help="authenticated user task")
    parser.add_argument(
        "--mode",
        default="plain",
        choices=("plain", "labeled", "spotlighting"),
        help="prompt construction mode",
    )
    parser.add_argument("--out", default=None, help="optional output path for the prompt")
    parser.add_argument("--json", action="store_true", help="emit structured JSON bundle")
    args = parser.parse_args(argv)

    try:
        observation = load_observation(args.obs)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    bundle = build_observation_prompt(
        observation,
        args.task,
        mode=PromptMode(args.mode),
    )
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(bundle.full_prompt, encoding="utf-8")

    if args.json:
        print(
            json.dumps(
                {
                    "observation_id": bundle.observation_id,
                    "mode": args.mode,
                    "region_count": bundle.region_count,
                    "untrusted_count": bundle.untrusted_count,
                    "system_prompt": bundle.system_prompt,
                    "user_prompt": bundle.user_prompt,
                },
                indent=2,
            )
        )
    else:
        print(bundle.full_prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
