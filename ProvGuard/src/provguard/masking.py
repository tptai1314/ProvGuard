"""Untrusted-set construction and trusted projection from paper Eqs. (3)-(4)."""

from __future__ import annotations

from dataclasses import replace

from .lattice import IntegrityLabel, leq
from .schemas import Observation, Region, Transcript

MASK_PLACEHOLDER = "<MASKED_BY_PROVGUARD>"


def is_untrusted(region: Region, clearance: IntegrityLabel) -> bool:
    """Paper Eq. (3): label above clearance or non-perceivable."""

    return not leq(region.label, clearance) or not region.provenance.perceivable


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

