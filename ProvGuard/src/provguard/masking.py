"""Untrusted-set construction, trusted projection, and pixel/tile masking (paper Eqs. 2-4)."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .contrast import load_rgb
from .lattice import IntegrityLabel, leq
from .schemas import BoundingBox, Observation, Region, Transcript

MASK_PLACEHOLDER = "<MASKED_BY_PROVGUARD>"
DEFAULT_MASK_RGB: tuple[int, int, int] = (128, 128, 128)


def is_untrusted(region: Region, clearance: IntegrityLabel) -> bool:
    """Paper Eq. (3): label above clearance or non-perceivable."""

    return not leq(region.label, clearance) or not region.provenance.perceivable


def untrusted_observation_region_ids(
    observation: Observation, clearance: IntegrityLabel
) -> frozenset[str]:
    """Return untrusted/imperceptible region IDs within a single observation."""

    return frozenset(
        region.region_id
        for region in observation.regions
        if is_untrusted(region, clearance)
    )


def untrusted_region_ids(transcript: Transcript, clearance: IntegrityLabel) -> frozenset[str]:
    return frozenset(
        region.region_id
        for observation in transcript.observations
        for region in observation.regions
        if is_untrusted(region, clearance)
    )


def mask_observation(
    observation: Observation,
    region_ids: frozenset[str],
    placeholder: str = MASK_PLACEHOLDER,
) -> Observation:
    """Paper Definition 12: replace content and preserve geometry/metadata."""

    return replace(
        observation,
        regions=tuple(
            region.masked(placeholder) if region.region_id in region_ids else region
            for region in observation.regions
        ),
    )


def trusted_projection(
    transcript: Transcript,
    region_ids: frozenset[str],
    placeholder: str = MASK_PLACEHOLDER,
) -> Transcript:
    """Paper Eq. (4): task, action history, and all masked observations."""

    return replace(
        transcript,
        observations=tuple(
            mask_observation(observation, region_ids, placeholder)
            for observation in transcript.observations
        ),
    )


def snap_box_to_tiles(
    box: BoundingBox,
    width: int,
    height: int,
    tile_size: int | None = None,
) -> BoundingBox:
    """Snap a bounding box outward to covering tiles (paper Eq. 2 tile-label join)."""

    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive")
    if tile_size is not None and tile_size > 0:
        left = float(max(0, (math.floor(box.left) // tile_size) * tile_size))
        top = float(max(0, (math.floor(box.top) // tile_size) * tile_size))
        right = float(min(width, math.ceil(box.right / tile_size) * tile_size))
        bottom = float(min(height, math.ceil(box.bottom / tile_size) * tile_size))
    else:
        left = float(max(0, min(width, round(box.left))))
        top = float(max(0, min(height, round(box.top))))
        right = float(max(0, min(width, round(box.right))))
        bottom = float(max(0, min(height, round(box.bottom))))
    right = max(right, left)
    bottom = max(bottom, top)
    return BoundingBox(left=left, top=top, right=right, bottom=bottom)


def mask_image_array(
    rgb: NDArray[np.uint8],
    boxes: Iterable[BoundingBox],
    *,
    fill_rgb: tuple[int, int, int] = DEFAULT_MASK_RGB,
    tile_size: int | None = None,
) -> tuple[NDArray[np.uint8], int]:
    """Paint constant fill over the specified boxes in an (H,W,3) RGB image."""

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Expected an (H,W,3) RGB uint8 array")
    height, width = int(rgb.shape[0]), int(rgb.shape[1])
    masked = rgb.copy()
    mask_bitmap = np.zeros((height, width), dtype=bool)
    fill_pixel = np.asarray(fill_rgb, dtype=np.uint8)

    for box in boxes:
        snapped = snap_box_to_tiles(box, width, height, tile_size)
        x0, y0 = round(snapped.left), round(snapped.top)
        x1, y1 = round(snapped.right), round(snapped.bottom)
        if x1 > x0 and y1 > y0:
            masked[y0:y1, x0:x1] = fill_pixel
            mask_bitmap[y0:y1, x0:x1] = True

    return masked, int(mask_bitmap.sum())


def mask_observation_image(
    rgb: NDArray[np.uint8],
    observation: Observation,
    region_ids: frozenset[str],
    *,
    fill_rgb: tuple[int, int, int] = DEFAULT_MASK_RGB,
    tile_size: int | None = None,
) -> tuple[NDArray[np.uint8], int]:
    """Mask all regions in ``region_ids`` on the given RGB screenshot array."""

    boxes = [
        region.geometry.bounds
        for region in observation.regions
        if region.region_id in region_ids
    ]
    return mask_image_array(rgb, boxes, fill_rgb=fill_rgb, tile_size=tile_size)


def encode_image_png(rgb: NDArray[np.uint8]) -> bytes:
    """Encode an (H,W,3) RGB uint8 array as PNG bytes."""

    from PIL import Image

    buffer = BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def save_masked_image(
    image_path: str | Path,
    out_path: str | Path,
    observation: Observation,
    region_ids: frozenset[str],
    *,
    fill_rgb: tuple[int, int, int] = DEFAULT_MASK_RGB,
    tile_size: int | None = None,
) -> dict[str, int]:
    """Load a screenshot, mask regions in ``region_ids``, and save the masked PNG."""

    from PIL import Image

    rgb = load_rgb(image_path)
    masked_rgb, masked_pixels = mask_observation_image(
        rgb,
        observation,
        region_ids,
        fill_rgb=fill_rgb,
        tile_size=tile_size,
    )
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(masked_rgb, mode="RGB").save(destination, format="PNG")
    total_pixels = int(rgb.shape[0] * rgb.shape[1])
    return {
        "width": int(rgb.shape[1]),
        "height": int(rgb.shape[0]),
        "total_pixels": total_pixels,
        "masked_pixels": masked_pixels,
        "masked_regions": sum(1 for r in observation.regions if r.region_id in region_ids),
    }
