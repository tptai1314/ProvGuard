"""Parser for `adb shell dumpsys window windows`.

Only the fields the Label Service needs are extracted: owner UID, window type,
frame, alpha, visibility and the window token used by the dispatcher. The parser is
tolerant: unknown fields are ignored, and a window that cannot be parsed is skipped
rather than aborting the whole observation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import BoundingBox, WindowType

_HEADER_RE = re.compile(r"^\s*Window #(\d+) Window\{(\w+) u(\d+) (.+?)\}:\s*$")
_TYPE_RE = re.compile(r"(?<![A-Za-z])ty=([A-Z_0-9]+)")
_FRAME_RE = re.compile(
    r"^\s*Frames:.*?\bframe=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", re.MULTILINE
)
_PACKAGE_RE = re.compile(r"(?<![A-Za-z])package=(\S+)")
_UID_RE = re.compile(r"mOwnerUid=(-?\d+)")
_ALPHA_RE = re.compile(r"mShownAlpha=([0-9.]+)\s+mAlpha=([0-9.]+)")
_MTOKEN_RE = re.compile(r"mToken=(\S+\{[^}]*\}|[^\s]+)")
_DISPLAY_BOUNDS_RE = re.compile(r"mBounds=Rect\((-?\d+),\s*(-?\d+)\s*-\s*(-?\d+),\s*(-?\d+)\)")

_TYPE_MAP: dict[str, WindowType] = {
    "BASE_APPLICATION": WindowType.APPLICATION,
    "APPLICATION": WindowType.APPLICATION,
    "ACTIVITY": WindowType.APPLICATION,
    "APPLICATION_OVERLAY": WindowType.OVERLAY,
    "SYSTEM_ALERT": WindowType.OVERLAY,
    "TOAST": WindowType.OVERLAY,
    "PRIORITY_PHONE": WindowType.OVERLAY,
    "ACCESSIBILITY_OVERLAY": WindowType.OVERLAY,
    "NOTIFICATION_SHADE": WindowType.SHADE,
    "SHADE": WindowType.SHADE,
    "STATUS_BAR": WindowType.SYSTEM,
    "NAVIGATION_BAR": WindowType.SYSTEM,
    "NAVIGATION_BAR_PANEL": WindowType.SYSTEM,
    "TASKBAR": WindowType.SYSTEM,
    "WALLPAPER": WindowType.SYSTEM,
    "DREAM": WindowType.SYSTEM,
    "SCREENSAVER": WindowType.SYSTEM,
    "VOLUME_OVERLAY": WindowType.SYSTEM,
    "MAGNIFICATION_OVERLAY": WindowType.OVERLAY,
    "INPUT_METHOD": WindowType.IME,
}


@dataclass(frozen=True)
class WindowInfo:
    index: int
    token: str
    name: str
    package: str
    uid: int
    type_name: str
    window_type: WindowType
    frame: BoundingBox
    alpha: float
    visible: bool
    on_screen: bool
    obscured: bool
    has_surface: bool

    @property
    def area(self) -> float:
        return self.frame.area


def map_window_type(type_name: str, uid: int) -> WindowType:
    if type_name in _TYPE_MAP:
        return _TYPE_MAP[type_name]
    if "OVERLAY" in type_name:
        return WindowType.OVERLAY
    return WindowType.SYSTEM if uid < 10000 else WindowType.APPLICATION


def _parse_alpha(block: str) -> float:
    match = _ALPHA_RE.search(block)
    if match is None:
        return 1.0
    shown, requested = (float(part) for part in match.groups())
    return max(0.0, min(1.0, max(shown, requested)))


def _parse_block(index: int, token: str, name: str, block: str) -> WindowInfo | None:
    package_match = _PACKAGE_RE.search(block)
    uid_match = _UID_RE.search(block)
    type_match = _TYPE_RE.search(block)
    frame_match = _FRAME_RE.search(block)
    if package_match is None or uid_match is None or frame_match is None:
        return None
    left, top, right, bottom = (float(part) for part in frame_match.groups())
    right = max(right, left)
    bottom = max(bottom, top)
    uid = int(uid_match.group(1))
    type_name = type_match.group(1) if type_match else "UNKNOWN"
    token_match = _MTOKEN_RE.search(block)
    token_value = token_match.group(1) if token_match else token
    return WindowInfo(
        index=index,
        token=token_value,
        name=name,
        package=package_match.group(1),
        uid=uid,
        type_name=type_name,
        window_type=map_window_type(type_name, uid),
        frame=BoundingBox(left=left, top=top, right=right, bottom=bottom),
        alpha=_parse_alpha(block),
        visible=("isVisible=true" in block) and ("mViewVisibility=0x0" in block),
        on_screen="isOnScreen=true" in block,
        obscured="mObscured=true" in block,
        has_surface="mHasSurface=true" in block,
    )


def parse_window_dump(text: str) -> list[WindowInfo]:
    """Return windows in dump order (index 0 is the topmost window)."""

    windows: list[WindowInfo] = []
    current: tuple[int, str, str, list[str]] | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        index, token, name, lines = current
        parsed = _parse_block(index, token, name, "\n".join(lines))
        if parsed is not None:
            windows.append(parsed)
        current = None

    for line in text.splitlines():
        header = _HEADER_RE.match(line)
        if header is not None:
            flush()
            index, token, _uid, name = header.groups()
            current = (int(index), token, name.strip(), [])
            continue
        if current is not None:
            current[3].append(line)
    flush()
    windows.sort(key=lambda window: window.index)
    return windows


def display_size_from_dump(text: str) -> tuple[int, int] | None:
    """Extract the display size from the first `mBounds=Rect(...)` occurrence."""

    match = _DISPLAY_BOUNDS_RE.search(text)
    if match is None:
        return None
    left, top, right, bottom = (int(part) for part in match.groups())
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None
    return width, height
