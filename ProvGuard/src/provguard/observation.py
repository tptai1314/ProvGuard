"""Build a labelled :class:`Observation` from a real Android dump.

Inputs are the three raw artefacts collected from the device (UI XML, window dump,
screenshot) plus optional active notifications. The output uses the paper's data
model, so every downstream experiment reads exactly the objects used in the formal
proofs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .contrast import region_luminance, text_background_luminance
from .labeling import DefaultLabelingPolicy
from .lattice import IntegrityLabel, parse_integrity_label
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
    represented_window_tokens: set[str] = set()
    represented_window_indices: set[int] = set()
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
            f"{node.bounds.right:.0f},{node.bounds.bottom:.0f}".encode()
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
        if not used_fallback:
            represented_window_tokens.add(window.token)
            represented_window_indices.add(window.index)

    # Synthesize untrusted TILE regions for visible overlay/shade windows omitted by uiautomator dump
    for window in windows:
        if not (window.visible and window.on_screen) or window.alpha <= 0.0:
            continue
        if window.window_type not in {WindowType.OVERLAY, WindowType.SHADE}:
            continue
        if window.index in represented_window_indices or window.token in represented_window_tokens:
            continue
        if target_package and window.package == target_package:
            continue
        if window.package in _SYSTEM_PACKAGES and window.window_type == WindowType.OVERLAY:
            continue
        clipped = _intersection(window.frame, display_box)
        if clipped is None or clipped.area <= 0:
            continue
        synth_prov = ProvenanceRecord(
            uid=window.uid,
            window_type=window.window_type,
            web_origin=None,
            notification_sender=window.package if window.window_type == WindowType.SHADE else None,
            notification_sensitive=False,
            perceivable=True,
        )
        synth_label = policy.label(synth_prov)
        label_counts[synth_label.value] += 1
        synth_region = Region(
            region_id=f"win_{window.index}",
            kind=RegionKind.TILE,
            content=f"[{window.window_type.value.upper()} WINDOW: {window.package}]",
            geometry=Geometry(
                bounds=clipped,
                z_order=window.index,
                class_name=f"window:{window.type_name}",
                clickable=False,
                editable=False,
                touchable=True,
            ),
            provenance=synth_prov,
            label=synth_label,
            binding=Binding(
                window_token=window.token,
                node_id=None,
                digest="",
                owner_uid=window.uid,
            ),
            metadata={
                "window_name": window.name,
                "window_token": window.token,
                "package": window.package,
                "synthesized_from_window_dump": True,
            },
        )
        regions.append(synth_region)

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


def region_from_dict(data: dict[str, Any]) -> Region:
    """Deserialize a region dictionary from ``labels.json`` back to a :class:`Region`."""

    bounds_raw = data.get("bounds", [0.0, 0.0, 0.0, 0.0])
    bounds = BoundingBox(
        left=float(bounds_raw[0]),
        top=float(bounds_raw[1]),
        right=float(bounds_raw[2]),
        bottom=float(bounds_raw[3]),
    )
    prov_raw = data.get("provenance", {})
    provenance = ProvenanceRecord(
        uid=int(prov_raw.get("uid", 0)),
        window_type=WindowType(prov_raw.get("window_type", WindowType.APPLICATION.value)),
        web_origin=prov_raw.get("web_origin"),
        notification_sender=prov_raw.get("notification_sender"),
        notification_sensitive=bool(prov_raw.get("notification_sensitive", False)),
        perceivable=bool(prov_raw.get("perceivable", True)),
    )
    binding_raw = data.get("binding")
    binding = (
        None
        if binding_raw is None
        else Binding(
            window_token=str(binding_raw["window_token"]),
            node_id=binding_raw.get("node_id"),
            digest=binding_raw.get("digest"),
            owner_uid=int(binding_raw.get("owner_uid", provenance.uid)),
        )
    )
    return Region(
        region_id=str(data["region_id"]),
        kind=RegionKind(data.get("kind", RegionKind.NODE.value)),
        content=str(data.get("content", "")),
        geometry=Geometry(
            bounds=bounds,
            z_order=int(data.get("z_order", 0)),
            class_name=str(data.get("class_name", "")),
            clickable=bool(data.get("clickable", False)),
            editable=bool(data.get("editable", False)),
            touchable=bool(data.get("touchable", data.get("clickable", False))),
        ),
        provenance=provenance,
        label=parse_integrity_label(data.get("label", IntegrityLabel.APP.value)),
        binding=binding,
        metadata=dict(data.get("metadata", {})),
    )


def observation_from_dict(payload: dict[str, Any]) -> Observation:
    """Deserialize a ``labels.json`` (or wrapped case) payload into an :class:`Observation`."""

    if "regions" not in payload and isinstance(payload.get("observation"), dict):
        payload = payload["observation"]
    display = payload.get("display", {})
    width = int(display.get("width", payload.get("display_width", 1080)))
    height = int(display.get("height", payload.get("display_height", 2400)))
    regions = tuple(region_from_dict(item) for item in payload.get("regions", []))
    return Observation(
        observation_id=str(payload.get("observation_id", "obs_0")),
        step=int(payload.get("step", 0)),
        regions=regions,
        display_width=width,
        display_height=height,
    )


def serialize_observation(observation: Observation) -> dict[str, Any]:
    """Serialize any :class:`Observation` (including masked ones) to the JSON schema."""

    return observation_to_dict(
        BuildResult(
            observation=observation,
            diagnostics={
                "regions": len(observation.regions),
                "perceivable": sum(1 for r in observation.regions if r.provenance.perceivable),
                "label_counts": {
                    label.value: sum(1 for r in observation.regions if r.label == label)
                    for label in IntegrityLabel
                },
            },
        )
    )


def load_observation(path: str | Path) -> Observation:
    """Load an :class:`Observation` from a ``labels.json`` file or an observation folder."""

    target = Path(path)
    if target.is_dir():
        labels_file = target / "labels.json"
        if not labels_file.exists():
            raise FileNotFoundError(
                f"No labels.json found in {target}. Run scripts/labels.py --obs {target} first."
            )
        target = labels_file
    payload = json.loads(target.read_text(encoding="utf-8"))
    return observation_from_dict(payload)
