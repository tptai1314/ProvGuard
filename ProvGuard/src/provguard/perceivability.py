"""Conservative perceivability tests P1-P4 from paper Definition 3."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import prod


@dataclass(frozen=True)
class PerceivabilityThresholds:
    on_screen_fraction: float = 0.5
    visible_fraction: float = 0.5
    minimum_contrast: float = 3.0
    minimum_alpha: float = 0.05
    maximum_occluding_opacity: float = 0.8

    def __post_init__(self) -> None:
        if not 0 < self.on_screen_fraction <= 1:
            raise ValueError("on_screen_fraction must be in (0,1]")
        if not 0 < self.visible_fraction <= 1:
            raise ValueError("visible_fraction must be in (0,1]")
        if self.minimum_contrast < 1:
            raise ValueError("minimum_contrast must be at least 1")
        if not 0 <= self.minimum_alpha < 1:
            raise ValueError("minimum_alpha must be in [0,1)")
        if not 0 <= self.maximum_occluding_opacity <= 1:
            raise ValueError("maximum_occluding_opacity must be in [0,1]")


@dataclass(frozen=True)
class PerceivabilityEvidence:
    on_screen_fraction: float | None
    visible_fraction: float | None
    text_luminance: float | None
    background_luminance: float | None
    effective_alpha: float | None
    drawn_area: float | None
    text_bearing: bool = True


def combined_opacity(opacities: Iterable[float]) -> float:
    """Paper Definition 3(P2): 1 - product_i(1-alpha_i)."""

    values = tuple(opacities)
    if any(alpha < 0 or alpha > 1 for alpha in values):
        raise ValueError("Opacities must be in [0,1]")
    return 1.0 - prod(1.0 - alpha for alpha in values)


def contrast_ratio(first_luminance: float, second_luminance: float) -> float:
    """Paper Definition 3(P3), using relative luminances in [0,1]."""

    if not 0 <= first_luminance <= 1 or not 0 <= second_luminance <= 1:
        raise ValueError("Relative luminances must be in [0,1]")
    high, low = sorted((first_luminance, second_luminance), reverse=True)
    return (high + 0.05) / (low + 0.05)


def is_perceivable(
    evidence: PerceivabilityEvidence,
    thresholds: PerceivabilityThresholds,
) -> bool:
    """Evaluate P1-P4; unavailable evidence conservatively returns False."""

    required = (
        evidence.on_screen_fraction,
        evidence.visible_fraction,
        evidence.effective_alpha,
        evidence.drawn_area,
    )
    if any(value is None for value in required):
        return False
    assert evidence.on_screen_fraction is not None
    assert evidence.visible_fraction is not None
    assert evidence.effective_alpha is not None
    assert evidence.drawn_area is not None
    if evidence.on_screen_fraction < thresholds.on_screen_fraction:
        return False
    if evidence.visible_fraction < thresholds.visible_fraction:
        return False
    if evidence.effective_alpha <= thresholds.minimum_alpha or evidence.drawn_area <= 0:
        return False
    if evidence.text_bearing:
        if evidence.text_luminance is None or evidence.background_luminance is None:
            return False
        if contrast_ratio(evidence.text_luminance, evidence.background_luminance) < thresholds.minimum_contrast:
            return False
    return True

