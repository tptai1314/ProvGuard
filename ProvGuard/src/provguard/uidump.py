"""Parser for `adb shell uiautomator dump` XML.

The dump is the closest userspace equivalent of the labelled accessibility tree the
paper assumes. Each XML node becomes a :class:`UiNode` with a stable path, so that
the same node can be referred to across steps of one observation.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .schemas import BoundingBox

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


@dataclass(frozen=True)
class UiNode:
    path: str
    package: str
    class_name: str
    text: str
    content_desc: str
    hint: str
    resource_id: str
    bounds: BoundingBox
    clickable: bool
    enabled: bool
    depth: int

    @property
    def content(self) -> str:
        return self.text or self.content_desc or self.hint

    @property
    def has_text(self) -> bool:
        return bool(self.content.strip())


def _parse_bounds(value: str | None) -> BoundingBox:
    if not value:
        return BoundingBox(0.0, 0.0, 0.0, 0.0)
    match = _BOUNDS_RE.search(value)
    if match is None:
        return BoundingBox(0.0, 0.0, 0.0, 0.0)
    left, top, right, bottom = (float(part) for part in match.groups())
    right = max(right, left)
    bottom = max(bottom, top)
    return BoundingBox(left=left, top=top, right=right, bottom=bottom)


def _flag(element: ET.Element, name: str) -> bool:
    return element.get(name, "false").strip().lower() == "true"


def _make_node(element: ET.Element, path: str, depth: int) -> UiNode:
    return UiNode(
        path=path,
        package=element.get("package", ""),
        class_name=element.get("class", ""),
        text=element.get("text", ""),
        content_desc=element.get("content-desc", ""),
        hint=element.get("hint", ""),
        resource_id=element.get("resource-id", ""),
        bounds=_parse_bounds(element.get("bounds")),
        clickable=_flag(element, "clickable"),
        enabled=_flag(element, "enabled"),
        depth=depth,
    )


def parse_ui_xml(path: str | Path) -> list[UiNode]:
    """Flatten the accessibility tree into a list of nodes in dump order."""

    root = ET.parse(path).getroot()
    nodes: list[UiNode] = []

    def walk(element: ET.Element, prefix: str, depth: int) -> None:
        index = 0
        for child in element:
            if child.tag != "node":
                continue
            path_part = f"{prefix}.{index}" if prefix else str(index)
            nodes.append(_make_node(child, path_part, depth))
            walk(child, path_part, depth + 1)
            index += 1

    walk(root, "", 0)
    return nodes
