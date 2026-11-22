#!/usr/bin/env python3
"""Mask untrusted/imperceptible text regions and screenshot tiles (Tier 2 - C9)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provguard.io import write_json
from provguard.lattice import parse_integrity_label
from provguard.masking import (
    MASK_PLACEHOLDER,
    mask_observation,
    save_masked_image,
    untrusted_observation_region_ids,
)
from provguard.observation import load_observation, serialize_observation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observation directory or labels.json path")
    parser.add_argument(
        "--clearance",
        default="app",
        help="required integrity clearance (usr, sys, app, web, sdk, ntf, unt)",
    )
    parser.add_argument("--placeholder", default=MASK_PLACEHOLDER)
    parser.add_argument("--image", default=None, help="optional screenshot PNG to mask")
    parser.add_argument("--tile-size", type=int, default=32, help="tile size in pixels (0=exact box)")
    parser.add_argument("--out-labels", default=None, help="output path for masked labels.json")
    parser.add_argument("--out-image", default=None, help="output path for masked screen.png")
    args = parser.parse_args(argv)

    try:
        observation = load_observation(args.obs)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    clearance = parse_integrity_label(args.clearance)
    region_ids = untrusted_observation_region_ids(observation, clearance)
    masked_obs = mask_observation(observation, region_ids, placeholder=args.placeholder)

    obs_path = Path(args.obs)
    base_dir = obs_path if obs_path.is_dir() else obs_path.parent
    out_labels = Path(args.out_labels) if args.out_labels else base_dir / "masked_labels.json"
    write_json(out_labels, serialize_observation(masked_obs))

    image_stats: dict[str, int] | None = None
    image_in = Path(args.image) if args.image else base_dir / "raw" / "screen.png"
    if args.image or image_in.exists():
        out_img = Path(args.out_image) if args.out_image else base_dir / "masked_screen.png"
        tile_sz = args.tile_size if args.tile_size > 0 else None
        image_stats = save_masked_image(
            image_in,
            out_img,
            observation,
            region_ids,
            tile_size=tile_sz,
        )

    summary = {
        "observation_id": observation.observation_id,
        "clearance": clearance.value,
        "regions_total": len(observation.regions),
        "regions_masked": len(region_ids),
        "untrusted_region_ids": sorted(region_ids),
        "out_labels": str(out_labels),
        "image_masking": image_stats,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
