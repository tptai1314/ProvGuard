"""Dispatch Binder reference model for paper Algorithm 3."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from .actions import resolve_target
from .schemas import (
    Action,
    DispatchResult,
    DispatchStatus,
    LiveWindow,
    Observation,
)


@dataclass
class DispatchBinder:
    """Simulate atomic window checks; real atomicity requires AOSP integration."""

    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def dispatch(
        self,
        action: Action,
        observation: Observation,
        live_windows: tuple[LiveWindow, ...],
    ) -> DispatchResult:
        target = resolve_target(action, observation)
        if target is None or target.binding is None:
            return DispatchResult(DispatchStatus.REOBSERVE, "target or binding is missing")
        binding = target.binding
        with self._lock:
            window = next((w for w in live_windows if w.token == binding.window_token), None)
            if window is None:
                return DispatchResult(DispatchStatus.REOBSERVE, "observed window no longer exists")
            if window.owner_uid != binding.owner_uid:
                return DispatchResult(DispatchStatus.REOBSERVE, "window owner changed")
            if action.coordinates is not None:
                x, y = action.coordinates
                top = max(
                    (w for w in live_windows if w.touchable_at(x, y)),
                    key=lambda item: item.z_order,
                    default=None,
                )
                if top is None or top.token != binding.window_token:
                    return DispatchResult(
                        DispatchStatus.REOBSERVE,
                        "observed window is not topmost touchable target",
                    )
            if binding.node_id is not None:
                digest = window.nodes.get(binding.node_id)
                if digest is None or digest != binding.digest:
                    return DispatchResult(
                        DispatchStatus.REOBSERVE,
                        "node identity or digest changed",
                    )
            return DispatchResult(
                DispatchStatus.DELIVERED,
                "binding matched at dispatch",
                window.token,
            )

