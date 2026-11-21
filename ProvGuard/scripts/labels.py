#!/usr/bin/env python3
"""Build ``labels.json`` and ``regions.jsonl`` from a captured observation.

Reads ``<obs>/raw/{ui.xml,windows.txt,screen.png,notifications.txt}`` and an optional
``<obs>/meta.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provguard.contrast import luminosity_for_image
from provguard.io import write_json, write_jsonl
from provguard.notifications import parse_notification_dump
from provguard.observation import BuildSettings, build_observation, observation_to_dict
from provguard.perceivability import PerceivabilityThresholds
from provguard.uidump import parse_ui_xml
from provguard.windowdump import display_size_from_dump, parse_window_dump


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _window_summary(windows: list) -> list[dict[str, object]]:
    return [
        {
            "index": window.index,
            "package": window.package,
            "uid": window.uid,
            "type": window.type_name,
            "window_type": window.window_type.value,
            "frame": [window.frame.left, window.frame.top, window.frame.right, window.frame.bottom],
            "alpha": window.alpha,
            "visible": window.visible,
            "on_screen": window.on_screen,
            "obscured": window.obscured,
        }
        for window in windows
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observation directory")
    parser.add_argument("--out", default=None, help="labels.json path")
    parser.add_argument("--target-app", default=None, help="package of the app under test")
    parser.add_argument("--no-image", action="store_true", help="skip contrast (P3)")
    parser.add_argument("--on-screen", type=float, default=0.5)
    parser.add_argument("--visible", type=float, default=0.5)
    parser.add_argument("--contrast", type=float, default=3.0)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)

    obs = Path(args.obs)
    raw = obs / "raw"
    for required in ("ui.xml", "windows.txt"):
        if not (raw / required).exists():
            print(f"error: missing {raw / required}", file=sys.stderr)
            return 2

    windows_text = _read_text(raw / "windows.txt")
    windows = parse_window_dump(windows_text)
    nodes = parse_ui_xml(raw / "ui.xml")

    notifications = []
    notifications_path = raw / "notifications.txt"
    if notifications_path.exists():
        notifications = parse_notification_dump(_read_text(notifications_path))

    meta: dict = {}
    meta_path = obs / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    display = None
    if isinstance(meta.get("display"), dict):
        display = (int(meta["display"]["width"]), int(meta["display"]["height"]))
    if display is None:
        display = display_size_from_dump(windows_text)
    if display is None:
        print("error: cannot determine display size (missing meta.json and mBounds)", file=sys.stderr)
        return 2

    luminance = None
    screen_path = raw / "screen.png"
    if not args.no_image and screen_path.exists():
        luminance = luminosity_for_image(screen_path)

    thresholds = PerceivabilityThresholds(
        on_screen_fraction=args.on_screen,
        visible_fraction=args.visible,
        minimum_contrast=args.contrast,
        minimum_alpha=args.alpha,
    )
    settings = BuildSettings(target_package=args.target_app, thresholds=thresholds)
    result = build_observation(
        observation_id=meta.get("observation_id", obs.name),
        step=0,
        nodes=nodes,
        windows=windows,
        display=display,
        settings=settings,
        luminance=luminance,
        notifications=notifications,
    )

    payload = observation_to_dict(
        result,
        extras={
            "source": {
                "observation_dir": str(obs),
                "meta": meta,
                "windows": _window_summary(windows),
                "notifications": [
                    {
                        "package": notification.package,
                        "title": notification.title,
                        "text": notification.text,
                        "importance": notification.importance,
                        "sensitive": notification.sensitive,
                    }
                    for notification in notifications
                ],
            }
        },
    )

    out = Path(args.out) if args.out else obs / "labels.json"
    write_json(out, payload)
    rows = [{"observation_id": payload["observation_id"], **region} for region in payload["regions"]]
    write_jsonl(out.parent / "regions.jsonl", rows)

    summary = {
        "observation_id": payload["observation_id"],
        "labels": str(out),
        "regions": str(out.parent / "regions.jsonl"),
        **result.diagnostics,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
