"""Tests for the `dumpsys window windows` parser."""

from __future__ import annotations

from pathlib import Path

from provguard.schemas import WindowType
from provguard.windowdump import display_size_from_dump, map_window_type, parse_window_dump

FIXTURE = Path(__file__).parent / "fixtures" / "obs_settings" / "windows.txt"


def _text() -> str:
    return FIXTURE.read_text(encoding="utf-8-sig")


def test_parses_three_windows_in_order() -> None:
    windows = parse_window_dump(_text())
    assert [window.index for window in windows] == [4, 5, 8]
    assert [window.package for window in windows] == [
        "com.android.systemui",
        "com.android.systemui",
        "com.android.settings",
    ]


def test_window_types_and_visibility() -> None:
    shade, status_bar, settings = parse_window_dump(_text())
    assert shade.window_type is WindowType.SHADE
    assert shade.visible is False
    assert status_bar.window_type is WindowType.SYSTEM
    assert status_bar.visible is True
    assert status_bar.frame.bottom == 142
    assert settings.window_type is WindowType.APPLICATION
    assert settings.uid == 1000
    assert settings.visible is True


def test_tokens_are_captured() -> None:
    settings = parse_window_dump(_text())[2]
    assert settings.token.startswith("ActivityRecord{")
    assert settings.name.startswith("com.android.settings/")


def test_display_size_from_dump() -> None:
    assert display_size_from_dump(_text()) == (1080, 2424)


def test_unknown_type_falls_back_by_uid() -> None:
    assert map_window_type("SOMETHING_NEW", 1000) is WindowType.SYSTEM
    assert map_window_type("SOMETHING_NEW", 10123) is WindowType.APPLICATION
    assert map_window_type("VENDOR_OVERLAY", 10123) is WindowType.OVERLAY
