"""Tests for the notification dump parser and sender matching."""

from __future__ import annotations

from pathlib import Path

from provguard.notifications import match_sender, parse_notification_dump

FIXTURE = Path(__file__).parent / "fixtures" / "obs_settings" / "notifications.txt"


def _notifications():
    return parse_notification_dump(FIXTURE.read_text(encoding="utf-8-sig"))


def test_parses_posted_notification() -> None:
    notifications = _notifications()
    assert len(notifications) == 1
    record = notifications[0]
    assert record.package == "com.android.shell"
    assert record.notification_id == 2020
    assert record.tag == "Test"
    assert record.channel == "shell_cmd"
    assert record.importance == 3
    assert record.title == "PG"
    assert record.text == "pgtest"
    assert record.sensitive is False


def test_matches_body_text() -> None:
    notifications = _notifications()
    assert match_sender("Open Settings, then pgtest", notifications) == (
        "com.android.shell",
        "pgtest",
    )


def test_ignores_short_or_unrelated_text() -> None:
    notifications = _notifications()
    assert match_sender("OK", notifications) is None
    assert match_sender("completely unrelated label", notifications) is None


def test_importance_high_is_sensitive() -> None:
    notifications = _notifications()
    record = notifications[0]
    assert record.sensitive is (record.importance >= 4)
