"""Build a labelled :class:`Observation` from a real Android dump.

Inputs are the three raw artefacts collected from the device (UI XML, window dump,
screenshot) plus optional active notifications. The output uses the paper's data
model, so every downstream experiment reads exactly the objects used in the formal
proofs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .contrast import region_luminance, text_background_luminance
from .labeling import DefaultLabelingPolicy
from .lattice import IntegrityLabel
from .notifications import ActiveNotification, match_sender
from .perceivability import (
    PerceivabilityEvidence,
    PerceivabilityThresholds,
    contrast_ratio,
    is_perceivable,
)
from .schemas import (
    Binding,
    BoundingBox,
    Geometry,
    Observation,
    ProvenanceRecord,
    Region,
    RegionKind,
    WindowType,
)
from .uidump import UiNode
from .windowdump import WindowInfo

_DEFAULT_SYSTEM_UIDS = frozenset({0, 1000})
_SYSTEM_PACKAGES = frozenset({"android", "com.android.systemui"})


@dataclass(frozen=True)
class BuildSettings:
    target_package: str | None = None
    thresholds: PerceivabilityThresholds = field(default_factory=PerceivabilityThresholds)
    notification_min_length: int = 4


@dataclass(frozen=True)
class BuildResult:
    observation: Observation
    diagnostics: dict[str, Any]


def _intersection(first: BoundingBox, second: BoundingBox) -> BoundingBox | None:
    left = max(first.left, second.left)
    top = max(first.top, second.top)
    right = min(first.right, second.right)
    bottom = min(first.bottom, second.bottom)
    if right <= left or bottom <= top:
        return None
    return BoundingBox(left=left, top=top, right=right, bottom=bottom)


def _center(box: BoundingBox) -> tuple[float, float]:
    return (box.left + box.right) / 2.0, (box.top + box.bottom) / 2.0


def _fallback_window(
    node: UiNode, target_package: str | None, target_uid: int, index: int
) -> WindowInfo:
    is_target = target_package is not None and node.package == target_package
    return WindowInfo(
        index=index,
        token="fallback",
        name=f"fallback:{node.package}",
        package=node.package,
        uid=target_uid if is_target else 0,
        type_name="BASE_APPLICATION" if is_target else "APPLICATION_OVERLAY",
        window_type=WindowType.APPLICATION if is_target else WindowType.OVERLAY,
        frame=node.bounds,
        alpha=1.0,
        visible=True,
        on_screen=True,
        obscured=False,
        has_surface=False,
    )


def _assign_window(
    node: UiNode,
    windows: list[WindowInfo],
    target_package: str | None,
    target_uid: int,
) -> tuple[WindowInfo, bool]:
    """Pick the window that owns a node; returns (window, used_fallback)."""

    center_x, center_y = _center(node.bounds)
    same_package = [window for window in windows if window.package == node.package]
    candidates = [
        window
        for window in same_package
        if window.visible and window.frame.contains(center_x, center_y)
    ]
    if not candidates:
        candidates = same_package
    if not candidates:
        candidates = [
            window
            for window in windows
            if window.visible and window.frame.contains(center_x, center_y)
        ]
    if candidates:
        return min(candidates, key=lambda window: window.index), False
    return _fallback_window(node, target_package, target_uid, len(windows)), True


def _visible_fraction(
    node: UiNode, window: WindowInfo, windows: list[WindowInfo]
) -> tuple[float, list[str]]:
    area = node.bounds.area
    if area <= 0:
        return 0.0, []
    combined = 0.0
    occluders: list[str] = []
    for other in windows:
        if other.index >= window.index or not other.visible or not other.has_surface:
            continue
        if other.alpha <= 0:
            continue
        overlap = _intersection(node.bounds, other.frame)
        if overlap is None:
            continue
        cover = overlap.area / area
        if cover <= 0:
            continue
        combined = 1.0 - (1.0 - combined) * (1.0 - min(1.0, other.alpha) * cover)
        if cover >= 0.01:
            occluders.append(other.name)
    return max(0.0, 1.0 - combined), occluders


def _target_window(
    windows: list[WindowInfo], explicit_package: str | None
) -> WindowInfo | None:
    applications = [
        window
        for window in windows
        if window.visible and window.window_type == WindowType.APPLICATION
    ]
    if explicit_package:
        for window in applications:
            if window.package == explicit_package:
                return window
    return min(applications, key=lambda window: window.index) if applications else None


def build_observation(
    *,
    observation_id: str,
    step: int,
    nodes: list[UiNode],
    windows: list[WindowInfo],
    display: tuple[int, int],
    settings: BuildSettings | None = None,
    luminance: NDArray[np.float64] | None = None,
    notifications: list[ActiveNotification] | None = None,
) -> BuildResult:
    """Turn raw device artefacts into a labelled observation."""

    config = settings or BuildSettings()
    notifications = notifications or []
    width, height = display
    display_box = BoundingBox(0.0, 0.0, float(width), float(height))

    target_window = _target_window(windows, config.target_package)
    target_package = (
        config.target_package
        or (target_window.package if target_window is not None else None)
    )
    target_uid = target_window.uid if target_window is not None else 0

    system_uids = set(_DEFAULT_SYSTEM_UIDS)
    system_uids.update(window.uid for window in windows if window.package in _SYSTEM_PACKAGES)
    policy = DefaultLabelingPolicy(
        target_app_uid=target_uid, system_uids=frozenset(system_uids)
    )

    regions: list[Region] = []
    label_counts: dict[str, int] = {label.value: 0 for label in IntegrityLabel}
    skipped_empty = 0
    fallback_count = 0
    perceivable_count = 0
    sender_matches = 0

    for node in nodes:
        if node.bounds.area <= 0:
            skipped_empty += 1
            continue

        window, used_fallback = _assign_window(node, windows, target_package, target_uid)
        fallback_count += 1 if used_fallback else 0

        on_screen_overlap = _intersection(node.bounds, display_box)
        on_screen_fraction = (
            on_screen_overlap.area / node.bounds.area if on_screen_overlap else 0.0
        )
        visible_fraction, occluders = _visible_fraction(node, window, windows)
        drawn_area = on_screen_overlap.area if on_screen_overlap else 0.0

        sender: str | None = None
        sensitive = False
        matched_text: str | None = None
        if node.has_text and notifications:
            match = match_sender(
                node.content,
                notifications,
                minimum_length=config.notification_min_length,
            )
            if match is not None:
                sender, matched_text = match
                sensitive = any(
                    notification.package == sender and notification.sensitive
                    for notification in notifications
                )
                sender_matches += 1

        contrast: float | None = None
        text_luminance: float | None = None
        background_luminance: float | None = None
        if node.has_text and luminance is not None:
            region_luminance_values = region_luminance(luminance, node.bounds)
            if region_luminance_values is not None and region_luminance_values.size >= 4:
                text_luminance, background_luminance = text_background_luminance(
                    region_luminance_values
                )
                contrast = contrast_ratio(text_luminance, background_luminance)

        evidence = PerceivabilityEvidence(
            on_screen_fraction=on_screen_fraction,
            visible_fraction=visible_fraction,
            text_luminance=text_luminance,
            background_luminance=background_luminance,
            effective_alpha=window.alpha if window.visible else 0.0,
            drawn_area=drawn_area,
            text_bearing=node.has_text,
        )
        perceivable = is_perceivable(evidence, config.thresholds)
        perceivable_count += 1 if perceivable else 0

        provenance = ProvenanceRecord(
            uid=window.uid,
            window_type=window.window_type,
            web_origin=None,
            notification_sender=sender,
            notification_sensitive=sensitive,
            perceivable=perceivable,
        )
        label = policy.label(provenance)
        label_counts[label.value] += 1

        content = node.content
        digest = sha256(
            f"{node.package}|{node.class_name}|{content}|"
            f"{node.bounds.left:.0f},{node.bounds.top:.0f},"
            f"{node.bounds.right:.0f},{node.bounds.bottom:.0f}".encode("utf-8")
        ).hexdigest()[:16]
        node_id = f"{node.path}:{node.resource_id.rsplit('/', 1)[-1] or node.class_name.rsplit('.', 1)[-1]}"

        region = Region(
            region_id=f"r{node.path}",
            kind=RegionKind.NODE,
            content=content,
            geometry=Geometry(
                bounds=node.bounds,
                z_order=window.index,
                class_name=node.class_name,
                clickable=node.clickable,
                editable="EditText" in node.class_name,
                touchable=node.clickable,
            ),
            provenance=provenance,
            label=label,
            binding=Binding(
                window_token=window.token,
                node_id=node_id,
                digest=digest,
                owner_uid=window.uid,
            ),
            metadata={
                "resource_id": node.resource_id,
                "class_name": node.class_name,
                "window_name": window.name,
                "window_token": window.token,
                "on_screen_fraction": round(on_screen_fraction, 4),
                "visible_fraction": round(visible_fraction, 4),
                "contrast": None if contrast is None else round(contrast, 3),
                "occluders": occluders,
                "clickable": node.clickable,
                "depth": node.depth,
                "notification_match": matched_text,
                "fallback_window": used_fallback,
            },
        )
        regions.append(region)

    observation = Observation(
        observation_id=observation_id,
        step=step,
        regions=tuple(regions),
        display_width=width,
        display_height=height,
    )
    diagnostics: dict[str, Any] = {
        "nodes_total": len(nodes),
        "regions": len(regions),
        "skipped_empty": skipped_empty,
        "fallback_windows": fallback_count,
        "perceivable": perceivable_count,
        "notification_matches": sender_matches,
        "label_counts": label_counts,
        "target_package": target_package,
        "target_uid": target_uid,
        "display": {"width": width, "height": height},
        "thresholds": asdict(config.thresholds),
        "has_luminance": luminance is not None,
    }
    return BuildResult(observation=observation, diagnostics=diagnostics)


def _box_to_list(box: BoundingBox) -> list[float]:
    return [box.left, box.top, box.right, box.bottom]


def observation_to_dict(
    result: BuildResult,
    *,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observation = result.observation
    payload: dict[str, Any] = {
        "observation_id": observation.observation_id,
        "step": observation.step,
        "display": {
            "width": observation.display_width,
            "height": observation.display_height,
        },
        "diagnostics": result.diagnostics,
        "regions": [
            {
                "region_id": region.region_id,
                "kind": region.kind.value,
                "content": region.content,
                "bounds": _box_to_list(region.geometry.bounds),
                "z_order": region.geometry.z_order,
                "class_name": region.geometry.class_name,
                "clickable": region.geometry.clickable,
                "editable": region.geometry.editable,
                "touchable": region.geometry.touchable,
                "provenance": {
                    "uid": region.provenance.uid,
                    "window_type": region.provenance.window_type.value,
                    "web_origin": region.provenance.web_origin,
                    "notification_sender": region.provenance.notification_sender,
                    "notification_sensitive": region.provenance.notification_sensitive,
                    "perceivable": region.provenance.perceivable,
                },
                "label": region.label.value,
                "binding": None
                if region.binding is None
                else {
                    "window_token": region.binding.window_token,
                    "node_id": region.binding.node_id,
                    "digest": region.binding.digest,
                    "owner_uid": region.binding.owner_uid,
                },
                "metadata": region.metadata,
            }
            for region in observation.regions
        ],
    }
    if extras:
        payload.update(extras)
    return payload
