"""Action resolution and equivalence from paper Definitions 6 and 7."""

from __future__ import annotations

import re

from .schemas import Action, EquivalenceMode, Observation, Region


def resolve_target(action: Action, observation: Observation) -> Region | None:
    if action.target_region_id is not None:
        return observation.region(action.target_region_id)
    if action.coordinates is None:
        return None
    x, y = action.coordinates
    candidates = [
        region
        for region in observation.regions
        if region.geometry.clickable
        and region.geometry.touchable
        and region.geometry.bounds.contains(x, y)
    ]
    return max(candidates, key=lambda item: item.geometry.z_order, default=None)


def resolved_identity(action: Action, observation: Observation) -> tuple[str | None, str | None]:
    region = resolve_target(action, observation)
    if region is None or region.binding is None:
        return (None, None)
    return (region.binding.window_token, region.binding.node_id)


def normalize_argument(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def actions_equivalent(
    proposed: Action,
    candidate: Action,
    observation: Observation,
    mode: EquivalenceMode,
) -> bool:
    """Control equivalence, with normalized arguments added for strict equivalence."""

    if proposed.op != candidate.op:
        return False
    if resolved_identity(proposed, observation) != resolved_identity(candidate, observation):
        return False
    return mode == EquivalenceMode.CONTROL or normalize_argument(
        proposed.argument
    ) == normalize_argument(candidate.argument)

