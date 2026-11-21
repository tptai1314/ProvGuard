#!/usr/bin/env python3
"""Compute the WCAG contrast ratio of one screen region (P3 evidence)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.contrast import (
    luminosity_for_image,
    region_luminance,
    text_background_luminance,
)
from provguard.perceivability import contrast_ratio
from provguard.schemas import BoundingBox


def _parse_bbox(value: str) -> BoundingBox:
    parts = [part.strip() for part in value.replace(" ", ",").split(",") if part.strip()]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be left,top,right,bottom")
    try:
        left, top, right, bottom = (float(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid bbox: {value}") from exc
    if right <= left or bottom <= top:
        raise argparse.ArgumentTypeError("bbox must have positive width and height")
    return BoundingBox(left=left, top=top, right=right, bottom=bottom)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--bbox", required=True, type=_parse_bbox, help="left,top,right,bottom")
    parser.add_argument("--low", type=float, default=10.0, help="text luminance percentile")
    parser.add_argument("--high", type=float, default=90.0, help="background luminance percentile")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        luminance = luminosity_for_image(args.image)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    region = region_luminance(luminance, args.bbox)
    if region is None or region.size < 4:
        print("error: region is empty or outside the image", file=sys.stderr)
        return 2
    low, high = text_background_luminance(region, low_percentile=args.low, high_percentile=args.high)
    ratio = contrast_ratio(low, high)
    result = {
        "image": args.image,
        "bbox": [args.bbox.left, args.bbox.top, args.bbox.right, args.bbox.bottom],
        "text_luminance": round(low, 4),
        "background_luminance": round(high, 4),
        "contrast_ratio": round(ratio, 3),
        "pixels": int(region.size),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"contrast={ratio:.2f}  text_lum={low:.3f}  bg_lum={high:.3f}  "
            f"pixels={region.size}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
