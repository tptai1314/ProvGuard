"""WCAG contrast (paper Definition 3, P3) computed from real screenshots.

The reference model only needs relative luminances; this module turns pixels into
them. It is deliberately conservative: a region's contrast is estimated from the
10th/90th percentile luminances, so a text region with a bright image behind it is
less likely to be declared perceivable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .perceivability import contrast_ratio
from .schemas import BoundingBox

DEFAULT_TILE = 32
DEFAULT_LOW_PERCENTILE = 10.0
DEFAULT_HIGH_PERCENTILE = 90.0


def load_rgb(path: str | Path) -> NDArray[np.uint8]:
    """Load an image as an (H,W,3) uint8 array, raising a clear error on failure."""

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as image:
            return np.asarray(image.convert("RGB"), dtype=np.uint8)
    except (OSError, UnidentifiedImageError) as exc:  # pragma: no cover - platform dependent
        raise ValueError(f"Cannot read image {path}: {exc}") from exc


def _srgb_to_linear(channel: NDArray[np.float64]) -> NDArray[np.float64]:
    normalized = channel / 255.0
    return np.where(
        normalized <= 0.04045,
        normalized / 12.92,
        ((normalized + 0.055) / 1.055) ** 2.4,
    )


def relative_luminance(rgb: NDArray[np.uint8]) -> NDArray[np.float64]:
    """WCAG 2.1 relative luminance for an (H,W,3) sRGB image."""

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Expected an (H,W,3) RGB array")
    linear = _srgb_to_linear(rgb.astype(np.float64))
    return 0.2126 * linear[..., 0] + 0.7152 * linear[..., 1] + 0.0722 * linear[..., 2]


def luminosity_for_image(path: str | Path) -> NDArray[np.float64]:
    return relative_luminance(load_rgb(path))


def _clip_box(luminance: NDArray[np.float64], box: BoundingBox) -> tuple[int, int, int, int]:
    height, width = luminance.shape[:2]
    left = max(0, min(width, round(box.left)))
    top = max(0, min(height, round(box.top)))
    right = max(0, min(width, round(box.right)))
    bottom = max(0, min(height, round(box.bottom)))
    if right <= left or bottom <= top:
        return 0, 0, 0, 0
    return left, top, right, bottom


def region_luminance(luminance: NDArray[np.float64], box: BoundingBox) -> NDArray[np.float64] | None:
    left, top, right, bottom = _clip_box(luminance, box)
    if right <= left or bottom <= top:
        return None
    return luminance[top:bottom, left:right]


def text_background_luminance(
    region: NDArray[np.float64],
    *,
    low_percentile: float = DEFAULT_LOW_PERCENTILE,
    high_percentile: float = DEFAULT_HIGH_PERCENTILE,
) -> tuple[float, float]:
    """Estimate (text, background) luminances from the darker/lighter tails."""

    if region.size == 0:
        raise ValueError("Region is empty")
    low = float(np.percentile(region, low_percentile))
    high = float(np.percentile(region, high_percentile))
    return low, high


def region_contrast(
    luminance: NDArray[np.float64],
    box: BoundingBox,
    *,
    low_percentile: float = DEFAULT_LOW_PERCENTILE,
    high_percentile: float = DEFAULT_HIGH_PERCENTILE,
) -> float | None:
    """Return the estimated WCAG ratio for a region, or None when it is empty."""

    region = region_luminance(luminance, box)
    if region is None or region.size < 4:
        return None
    text, background = text_background_luminance(
        region, low_percentile=low_percentile, high_percentile=high_percentile
    )
    return contrast_ratio(text, background)


def tile_boxes(width: int, height: int, tile: int = DEFAULT_TILE) -> list[BoundingBox]:
    """Cover the display with fixed-size tiles (the screenshot-tile variant)."""

    if width <= 0 or height <= 0:
        raise ValueError("Display dimensions must be positive")
    if tile <= 0:
        raise ValueError("Tile size must be positive")
    boxes: list[BoundingBox] = []
    for top in range(0, height, tile):
        for left in range(0, width, tile):
            boxes.append(
                BoundingBox(
                    left=float(left),
                    top=float(top),
                    right=float(min(left + tile, width)),
                    bottom=float(min(top + tile, height)),
                )
            )
    return boxes


def mean_luminance(region: NDArray[np.float64]) -> float:
    if region.size == 0:
        raise ValueError("Region is empty")
    return float(region.mean())
