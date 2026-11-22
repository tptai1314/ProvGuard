"""Dispatch Binder reference model and live re-observation helpers (paper Algorithm 3, Tier 3 - C13)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from typing import TYPE_CHECKING

from .actions import resolve_target
from .observation import BuildSettings, build_observation
from .schemas import (
    Action,
    ActionOp,
    BoundingBox,
    DispatchResult,
    DispatchStatus,
    LiveWindow,
    Observation,
    WindowType,
)
from .uidump import parse_ui_xml
from .windowdump import display_size_from_dump, parse_window_dump

if TYPE_CHECKING:
    from .device import Adb

_TARGETLESS_OPS = frozenset({ActionOp.BACK, ActionOp.HOME, ActionOp.FINISH, ActionOp.LAUNCH})


@dataclass
class DispatchBinder:
    """Verify window token, owner UID, top-most touch target, and node digest at dispatch time."""

    verify_window_token: bool = True
    verify_node_digest: bool = True
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def dispatch(
        self,
        action: Action,
        observation: Observation,
        live_windows: tuple[LiveWindow, ...],
    ) -> DispatchResult:
        target = resolve_target(action, observation)
        if target is None or target.binding is None:
            if (
                action.op in _TARGETLESS_OPS
                and action.target_region_id is None
                and action.coordinates is None
            ):
                token = live_windows[0].token if live_windows else None
                return DispatchResult(
                    DispatchStatus.DELIVERED,
                    "targetless action requires no node binding",
                    token,
                )
            return DispatchResult(DispatchStatus.REOBSERVE, "target or binding is missing")

        binding = target.binding
        with self._lock:
            window = next((w for w in live_windows if w.token == binding.window_token), None)
            if self.verify_window_token:
                if window is None:
                    return DispatchResult(
                        DispatchStatus.REOBSERVE, "observed window no longer exists"
                    )
                if window.owner_uid != binding.owner_uid:
                    return DispatchResult(DispatchStatus.REOBSERVE, "window owner changed")

                cx = (target.geometry.bounds.left + target.geometry.bounds.right) / 2.0
                cy = (target.geometry.bounds.top + target.geometry.bounds.bottom) / 2.0
                x, y = action.coordinates if action.coordinates is not None else (cx, cy)
                top = max(
                    (w for w in live_windows if w.touchable_at(x, y)),
                    key=lambda item: item.z_order,
                    default=None,
                )
                if (action.coordinates is not None and top is None) or (
                    top is not None and top.token != binding.window_token
                ):
                    return DispatchResult(
                        DispatchStatus.REOBSERVE,
                        "observed window is not topmost touchable target",
                    )

            if self.verify_node_digest and binding.node_id is not None:
                if window is None:
                    return DispatchResult(
                        DispatchStatus.REOBSERVE, "observed window no longer exists"
                    )
                digest = window.nodes.get(binding.node_id)
                if digest is None and target.region_id in window.nodes:
                    digest = window.nodes.get(target.region_id)
                if digest is None or digest != binding.digest:
                    return DispatchResult(
                        DispatchStatus.REOBSERVE,
                        "node identity or digest changed",
                    )

            resolved_token = window.token if window is not None else binding.window_token
            return DispatchResult(
                DispatchStatus.DELIVERED,
                "binding matched at dispatch",
                resolved_token,
            )

    def verify_against_observation(
        self,
        action: Action,
        observed: Observation,
        live_observation: Observation,
    ) -> DispatchResult:
        """Verify ``action`` on ``observed`` against a fresh ``live_observation``."""

        live_windows = live_windows_from_observation(live_observation)
        return self.dispatch(action, observed, live_windows)


def live_windows_from_observation(observation: Observation) -> tuple[LiveWindow, ...]:
    """Construct :class:`LiveWindow` objects from a labelled :class:`Observation`.

    In ``Observation`` objects produced by :func:`build_observation`, ``region.geometry.z_order``
    stores the ``dumpsys window`` index (0 = topmost). Here we invert that index into
    ``LiveWindow.z_order`` (higher = topmost) so :class:`DispatchBinder`'s ``max(z_order)``
    always selects the topmost window covering a screen coordinate.
    """

    by_token: dict[str, list] = {}
    for region in observation.regions:
        if region.binding is None:
            continue
        by_token.setdefault(region.binding.window_token, []).append(region)

    live: list[LiveWindow] = []
    for token, regions in by_token.items():
        owner_uid = regions[0].binding.owner_uid
        min_dump_index = min(r.geometry.z_order for r in regions)
        is_overlay = any(
            r.provenance.window_type in {WindowType.OVERLAY, WindowType.SHADE}
            for r in regions
        )
        z_order = (2000 if is_overlay else 1000) - min_dump_index

        nodes: dict[str, str] = {}
        bounds_list: list[BoundingBox] = []
        for region in regions:
            if region.geometry.bounds.area > 0:
                bounds_list.append(region.geometry.bounds)
            if region.binding is not None and region.binding.digest is not None:
                if region.binding.node_id is not None:
                    nodes[region.binding.node_id] = region.binding.digest
                nodes[region.region_id] = region.binding.digest

        live.append(
            LiveWindow(
                token=token,
                owner_uid=owner_uid,
                touchable_bounds=tuple(bounds_list),
                z_order=z_order,
                nodes=nodes,
            )
        )
    live.sort(key=lambda item: item.z_order, reverse=True)
    return tuple(live)


def simulate_live_mutation(
    observation: Observation,
    kind: str,
    *,
    target_region_id: str | None = None,
) -> Observation:
    """Create a mutated copy of ``observation`` to test rebinding/desync detection."""

    mode = kind.strip().lower()
    if mode == "none":
        return observation

    target_window_token: str | None = None
    if target_region_id is not None:
        target_reg = observation.region(target_region_id)
        if target_reg is not None and target_reg.binding is not None:
            target_window_token = target_reg.binding.window_token

    mutated_regions = []
    for region in observation.regions:
        if region.binding is None:
            mutated_regions.append(region)
            continue

        if mode == "digest":
            if target_region_id is None or region.region_id == target_region_id:
                new_binding = replace(region.binding, digest="mutated_digest_00")
                mutated_regions.append(
                    replace(region, content=region.content + " [CHANGED]", binding=new_binding)
                )
            else:
                mutated_regions.append(region)
        elif mode == "token":
            if target_window_token is None or region.binding.window_token == target_window_token:
                new_binding = replace(region.binding, window_token="win_replaced_token")
                mutated_regions.append(replace(region, binding=new_binding))
            else:
                mutated_regions.append(region)
        elif mode == "uid":
            if target_window_token is None or region.binding.window_token == target_window_token:
                new_binding = replace(
                    region.binding, owner_uid=region.binding.owner_uid + 9999
                )
                mutated_regions.append(replace(region, binding=new_binding))
            else:
                mutated_regions.append(region)
        else:
            mutated_regions.append(region)

    if mode == "overlay":
        # Insert a full-screen untrusted overlay window on top of all existing regions
        from .lattice import IntegrityLabel
        from .schemas import Binding, Geometry, ProvenanceRecord, Region, RegionKind

        overlay_box = BoundingBox(0.0, 0.0, float(observation.display_width), float(observation.display_height))
        overlay_region = Region(
            region_id="r_attacker_overlay",
            kind=RegionKind.NODE,
            content="Clickjacking overlay",
            geometry=Geometry(bounds=overlay_box, z_order=0, clickable=True, touchable=True),
            provenance=ProvenanceRecord(
                uid=99999,
                window_type=WindowType.OVERLAY,
                perceivable=True,
            ),
            label=IntegrityLabel.UNTRUSTED,
            binding=Binding(
                window_token="win_attacker_overlay",
                node_id="overlay:root",
                digest="deadbeefdeadbeef",
                owner_uid=99999,
            ),
        )
        mutated_regions.insert(0, overlay_region)

    return replace(observation, regions=tuple(mutated_regions))


def capture_live_observation(
    adb: Adb,
    *,
    observation_id: str = "obs_live_reobserve",
    step: int = 0,
    target_package: str | None = None,
    scratch_dir: str = ".provguard_live",
) -> Observation:
    """Re-observe the live device over ADB (UI XML + window dump) for dispatch binding."""

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix=scratch_dir) as tmp:
        tmp_path = Path(tmp)
        ui_xml = tmp_path / "ui.xml"
        adb.shell("uiautomator dump /sdcard/provguard_live_ui.xml")
        adb.pull("/sdcard/provguard_live_ui.xml", ui_xml)
        windows_text = adb.shell("dumpsys window windows")

        nodes = parse_ui_xml(ui_xml)
        windows = parse_window_dump(windows_text)
        display = adb.screen_size() or display_size_from_dump(windows_text) or (1080, 2400)
        result = build_observation(
            observation_id=observation_id,
            step=step,
            nodes=nodes,
            windows=windows,
            display=display,
            settings=BuildSettings(target_package=target_package),
        )
        return result.observation
