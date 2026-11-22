"""The finite integrity lattice from paper Definition 4 and Eq. (2)."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from functools import reduce


class IntegrityLabel(str, Enum):
    USER = "usr"
    SYSTEM = "sys"
    APP = "app"
    WEB = "web"
    SDK = "sdk"
    NOTIFICATION = "ntf"
    UNTRUSTED = "unt"


_LABEL_ALIASES: dict[str, IntegrityLabel] = {
    "usr": IntegrityLabel.USER,
    "user": IntegrityLabel.USER,
    "sys": IntegrityLabel.SYSTEM,
    "system": IntegrityLabel.SYSTEM,
    "app": IntegrityLabel.APP,
    "application": IntegrityLabel.APP,
    "web": IntegrityLabel.WEB,
    "webview": IntegrityLabel.WEB,
    "sdk": IntegrityLabel.SDK,
    "ntf": IntegrityLabel.NOTIFICATION,
    "notification": IntegrityLabel.NOTIFICATION,
    "unt": IntegrityLabel.UNTRUSTED,
    "untrusted": IntegrityLabel.UNTRUSTED,
    "overlay": IntegrityLabel.UNTRUSTED,
}


def parse_integrity_label(value: str | IntegrityLabel) -> IntegrityLabel:
    """Parse either a canonical 3-letter code or a full label name."""

    if isinstance(value, IntegrityLabel):
        return value
    key = str(value).strip().lower()
    if key in _LABEL_ALIASES:
        return _LABEL_ALIASES[key]
    return IntegrityLabel(value)


_CHANNELS = {IntegrityLabel.WEB, IntegrityLabel.SDK, IntegrityLabel.NOTIFICATION}


def leq(left: IntegrityLabel, right: IntegrityLabel) -> bool:
    """Return left <= right in the paper's 'no more trustworthy' order."""

    if left == right or left == IntegrityLabel.USER or right == IntegrityLabel.UNTRUSTED:
        return True
    if left == IntegrityLabel.SYSTEM:
        return right in {IntegrityLabel.APP, *_CHANNELS}
    if left == IntegrityLabel.APP:
        return right in _CHANNELS
    return False


def join(left: IntegrityLabel, right: IntegrityLabel) -> IntegrityLabel:
    """Least upper bound; used for screenshot tiles in paper Eq. (2)."""

    if leq(left, right):
        return right
    if leq(right, left):
        return left
    return IntegrityLabel.UNTRUSTED


def meet(left: IntegrityLabel, right: IntegrityLabel) -> IntegrityLabel:
    if leq(left, right):
        return left
    if leq(right, left):
        return right
    return IntegrityLabel.APP


def join_all(labels: Iterable[IntegrityLabel]) -> IntegrityLabel:
    values = tuple(labels)
    if not values:
        raise ValueError("At least one contributing layer is required")
    return reduce(join, values)

