"""Tests for the uiautomator XML parser."""

from __future__ import annotations

from pathlib import Path

from provguard.uidump import parse_ui_xml

FIXTURE = Path(__file__).parent / "fixtures" / "obs_settings" / "ui.xml"


def test_parses_all_nodes() -> None:
    nodes = parse_ui_xml(FIXTURE)
    assert len(nodes) == 73
    assert {node.package for node in nodes} == {"com.android.settings"}


def test_paths_are_unique_and_stable() -> None:
    nodes = parse_ui_xml(FIXTURE)
    paths = [node.path for node in nodes]
    assert len(paths) == len(set(paths))
    assert paths[0] == "0"


def test_bounds_and_text_are_extracted() -> None:
    nodes = parse_ui_xml(FIXTURE)
    with_text = [node for node in nodes if node.has_text]
    assert len(with_text) == 20
    root = nodes[0]
    assert root.bounds.left == 0
    assert root.bounds.right == 1080
    assert root.class_name == "android.widget.FrameLayout"
    assert nodes[0].depth == 0


def test_content_prefers_text_then_description_then_hint() -> None:
    nodes = parse_ui_xml(FIXTURE)
    node = next(node for node in nodes if node.content)
    assert node.content == (node.text or node.content_desc or node.hint)
