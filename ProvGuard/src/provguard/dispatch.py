"""ADB action dispatcher with pre-send DispatchBinder verification (Tier 3 - C12)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .actions import resolve_target
from .binder import (
    DispatchBinder,
    capture_live_observation,
    live_windows_from_observation,
)
from .schemas import (
    Action,
    ActionOp,
    DispatchResult,
    DispatchStatus,
    LiveWindow,
    Observation,
)

if TYPE_CHECKING:
    from .device import Adb

_PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
_SWIPE_COORDS_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,"
    r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)"
    r"(?:\s*,\s*(\d+))?\s*$"
)
_SHELL_UNSAFE_RE = re.compile(r"([\"'`$\\;&|<>()])")


@dataclass(frozen=True)
class ExecutionRecord:
    status: DispatchStatus
    reason: str
    window_token: str | None
    commands: tuple[str, ...]
    executed: bool
    target_point: tuple[int, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "window_token": self.window_token,
            "commands": list(self.commands),
            "executed": self.executed,
            "target_point": list(self.target_point) if self.target_point else None,
        }


def resolve_action_point(action: Action, observation: Observation) -> tuple[int, int] | None:
    """Resolve the screen (x, y) pixel coordinates for ``action`` on ``observation``."""

    if action.coordinates is not None:
        return (round(action.coordinates[0]), round(action.coordinates[1]))
    target = resolve_target(action, observation)
    if target is None:
        return None
    box = target.geometry.bounds
    return (round((box.left + box.right) / 2.0), round((box.top + box.bottom) / 2.0))


def escape_adb_input_text(text: str) -> str:
    """Escape a string for ``adb shell input text`` (spaces -> %s, escape shell specials)."""

    cleaned = text.replace("\r", " ").replace("\n", " ")
    escaped = _SHELL_UNSAFE_RE.sub(r"\\\1", cleaned)
    return escaped.replace(" ", "%s")


def _plan_swipe_command(
    action: Action,
    observation: Observation,
    point: tuple[int, int] | None,
) -> str:
    arg = (action.argument or "up").strip()
    match = _SWIPE_COORDS_RE.match(arg)
    if match:
        x1, y1, x2, y2 = (round(float(match.group(i))) for i in range(1, 5))
        duration = int(match.group(5)) if match.group(5) else 300
        return f"input swipe {x1} {y1} {x2} {y2} {duration}"

    cx, cy = point or (observation.display_width // 2, observation.display_height // 2)
    dx = max(150, observation.display_width // 3)
    dy = max(250, observation.display_height // 3)
    direction = arg.lower()
    if direction == "down":
        x1, y1, x2, y2 = cx, max(50, cy - dy // 2), cx, min(observation.display_height - 50, cy + dy // 2)
    elif direction == "left":
        x1, y1, x2, y2 = min(observation.display_width - 50, cx + dx // 2), cy, max(50, cx - dx // 2), cy
    elif direction == "right":
        x1, y1, x2, y2 = max(50, cx - dx // 2), cy, min(observation.display_width - 50, cx + dx // 2), cy
    else:
        # Default "up" (scroll down content)
        x1, y1, x2, y2 = cx, min(observation.display_height - 50, cy + dy // 2), cx, max(50, cy - dy // 2)
    return f"input swipe {x1} {y1} {x2} {y2} 300"


def plan_adb_commands(action: Action, observation: Observation) -> list[str]:
    """Translate a validated :class:`Action` into ``adb shell`` input commands."""

    point = resolve_action_point(action, observation)

    if action.op == ActionOp.TAP:
        if point is None:
            raise ValueError("TAP action requires a valid target_region_id or coordinates")
        return [f"input tap {point[0]} {point[1]}"]

    if action.op == ActionOp.LONG_PRESS:
        if point is None:
            raise ValueError("LONG_PRESS action requires a valid target_region_id or coordinates")
        x, y = point
        return [f"input swipe {x} {y} {x} {y} 800"]

    if action.op == ActionOp.TYPE:
        commands: list[str] = []
        if point is not None:
            commands.append(f"input tap {point[0]} {point[1]}")
        if action.argument:
            escaped = escape_adb_input_text(action.argument)
            commands.append(f'input text "{escaped}"')
        if not commands:
            raise ValueError("TYPE action requires either a target or non-empty text argument")
        return commands

    if action.op == ActionOp.SWIPE:
        return [_plan_swipe_command(action, observation, point)]

    if action.op == ActionOp.BACK:
        return ["input keyevent KEYCODE_BACK"]

    if action.op == ActionOp.HOME:
        return ["input keyevent KEYCODE_HOME"]

    if action.op == ActionOp.LAUNCH:
        pkg = (action.argument or "").strip()
        if not _PACKAGE_RE.match(pkg):
            raise ValueError(f"LAUNCH action requires a valid package name in argument, got {pkg!r}")
        return [f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"]

    if action.op == ActionOp.FINISH:
        return []

    raise ValueError(f"Unsupported action operation: {action.op}")


@dataclass
class ActionDispatcher:
    """Mediate and dispatch agent actions over ADB after verifying dispatch-time bindings."""

    binder: DispatchBinder
    adb: Adb | None = None
    dry_run: bool = False
    verify_binding: bool = True

    def execute(
        self,
        action: Action,
        observation: Observation,
        *,
        live_observation: Observation | None = None,
        live_windows: tuple[LiveWindow, ...] | None = None,
    ) -> ExecutionRecord:
        point = resolve_action_point(action, observation)

        if self.verify_binding:
            windows = self._resolve_live_windows(
                observation,
                live_observation=live_observation,
                live_windows=live_windows,
            )
            result = self.binder.dispatch(action, observation, windows)
        else:
            result = DispatchResult(
                DispatchStatus.DELIVERED,
                "dispatch binder disabled",
                None,
            )

        if result.status != DispatchStatus.DELIVERED:
            return ExecutionRecord(
                status=result.status,
                reason=result.reason,
                window_token=result.window_token,
                commands=(),
                executed=False,
                target_point=point,
            )

        commands = tuple(plan_adb_commands(action, observation))
        executed = False
        if not self.dry_run and self.adb is not None:
            for cmd in commands:
                self.adb.shell(cmd)
            executed = True

        return ExecutionRecord(
            status=DispatchStatus.DELIVERED,
            reason=result.reason,
            window_token=result.window_token,
            commands=commands,
            executed=executed,
            target_point=point,
        )

    def _resolve_live_windows(
        self,
        observed: Observation,
        *,
        live_observation: Observation | None,
        live_windows: tuple[LiveWindow, ...] | None,
    ) -> tuple[LiveWindow, ...]:
        if live_windows is not None:
            return live_windows
        if live_observation is not None:
            return live_windows_from_observation(live_observation)
        if not self.dry_run and self.adb is not None:
            fresh = capture_live_observation(self.adb, step=observed.step)
            return live_windows_from_observation(fresh)
        return live_windows_from_observation(observed)
