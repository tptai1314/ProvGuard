"""Tests for WCAG contrast and tile geometry."""

from __future__ import annotations

import numpy as np
import pytest

from provguard.contrast import (
    region_contrast,
    relative_luminance,
    text_background_luminance,
    tile_boxes,
)
from provguard.schemas import BoundingBox


def test_relative_luminance_endpoints() -> None:
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    image[0, 0] = [255, 255, 255]
    luminance = relative_luminance(image)
    assert luminance[0, 0] == pytest.approx(1.0, abs=1e-6)
    assert luminance[1, 1] == pytest.approx(0.0, abs=1e-6)


def test_black_on_white_is_21() -> None:
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[:5] = 255
    luminance = relative_luminance(image)
    ratio = region_contrast(luminance, BoundingBox(0, 0, 10, 10))
    assert ratio == pytest.approx(21.0, rel=1e-3)


def test_text_background_percentiles() -> None:
    region = np.array([[0.0, 0.0, 1.0, 1.0]])
    text, background = text_background_luminance(region)
    assert text == pytest.approx(0.0)
    assert background == pytest.approx(1.0)


def test_region_contrast_rejects_empty_box() -> None:
    luminance = np.ones((10, 10), dtype=np.float64)
    assert region_contrast(luminance, BoundingBox(5, 5, 5, 5)) is None
    assert region_contrast(luminance, BoundingBox(20, 20, 30, 30)) is None


def test_tile_boxes_cover_display_and_clip_edges() -> None:
    boxes = tile_boxes(100, 70, tile=32)
    assert len(boxes) == 12
    assert boxes[0].left == 0 and boxes[0].right == 32
    assert boxes[-1].right == 100 and boxes[-1].bottom == 70
    total = sum(box.area for box in boxes)
    assert total == pytest.approx(100 * 70)


def test_tile_boxes_validate_input() -> None:
    with pytest.raises(ValueError):
        tile_boxes(0, 10)
    with pytest.raises(ValueError):
        tile_boxes(10, 10, tile=0)
