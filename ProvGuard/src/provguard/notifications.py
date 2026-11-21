"""Parser and matcher for active notifications from `dumpsys notification`.

v1 heuristic: a screen region is attributed to a notification sender when its text
contains the notification's title or body. This is intentionally conservative and
does not replace a real NotificationListenerService; it only supplies the `snd`
field when the evidence is on screen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_RECORD_RE = re.compile(
    r"NotificationRecord\(0x[0-9a-fA-F]+:\s+pkg=(\S+)\s+user=UserHandle\{\d+\}\s+"
    r"id=(-?\d+)\s+tag=(\S+)\s+importance=(\d+)\s+key=(.+?):"
)
_CHANNEL_RE = re.compile(r"Notification\(channel=(\S+)")
_TITLE_RE = re.compile(r"^\s*android\.title=String \((.*)\)\s*$")
_TEXT_RE = re.compile(r"^\s*android\.text=String \((.*)\)\s*$")
_BIG_TEXT_RE = re.compile(r"^\s*android\.bigText=String \((.*)\)\s*$")


@dataclass(frozen=True)
class ActiveNotification:
    package: str
    notification_id: int
    tag: str
    importance: int
    channel: str
    key: str
    title: str
    text: str

    @property
    def sensitive(self) -> bool:
        """Importance HIGH or above is used as the v1 sensitivity proxy."""

        return self.importance >= 4


def _clean(value: str) -> str:
    value = value.strip()
    return "" if value in {"null", "None", ""} else value


def parse_notification_dump(text: str) -> list[ActiveNotification]:
    """Parse the ``Notification List`` section; return [] when nothing is posted."""

    notifications: list[ActiveNotification] = []
    blocks: list[list[str]] = []
    current: list[str] | None = None

    for line in text.splitlines():
        if _RECORD_RE.search(line):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)

    for block in blocks:
        header = _RECORD_RE.search(block[0])
        if header is None:
            continue
        package, notification_id, tag, importance, key = header.groups()
        channel_match = _CHANNEL_RE.search(block[0])
        title = text = big_text = ""
        for line in block[1:]:
            if (match := _TITLE_RE.match(line)) is not None:
                title = _clean(match.group(1))
            elif (match := _TEXT_RE.match(line)) is not None:
                text = _clean(match.group(1))
            elif (match := _BIG_TEXT_RE.match(line)) is not None:
                big_text = _clean(match.group(1))
        notifications.append(
            ActiveNotification(
                package=package,
                notification_id=int(notification_id),
                tag=tag,
                importance=int(importance),
                channel=channel_match.group(1) if channel_match else "",
                key=key.strip(),
                title=title,
                text=text or big_text,
            )
        )
    return notifications


def match_sender(
    content: str,
    notifications: list[ActiveNotification],
    *,
    minimum_length: int = 4,
) -> tuple[str, str] | None:
    """Return (package, matched_text) for the strongest on-screen match."""

    normalized = " ".join(content.lower().split())
    if len(normalized) < minimum_length:
        return None
    best: tuple[int, str, str] | None = None
    for notification in notifications:
        for candidate in (notification.title, notification.text):
            value = " ".join(candidate.lower().split())
            if len(value) < minimum_length or value not in normalized:
                continue
            score = len(value)
            if best is None or score > best[0]:
                best = (score, notification.package, candidate)
    if best is None:
        return None
    return best[1], best[2]
