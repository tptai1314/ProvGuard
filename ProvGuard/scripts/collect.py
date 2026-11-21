#!/usr/bin/env python3
"""Capture one observation (UI XML, window dump, screenshot, notifications).

Output layout::

    <out>/<observation_id>/
        meta.json
        raw/ui.xml
        raw/windows.txt
        raw/screen.png
        raw/notifications.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from provguard.device import Adb, AdbError
from provguard.io import sha256_file, write_json

_DEVICE_PROPS = (
    "ro.build.fingerprint",
    "ro.build.version.sdk",
    "ro.build.version.release",
    "ro.product.model",
    "ro.product.manufacturer",
)


def _device_metadata(adb: Adb) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for prop in _DEVICE_PROPS:
        try:
            metadata[prop] = adb.getprop(prop)
        except AdbError:
            metadata[prop] = "unknown"
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="obs", help="output root directory")
    parser.add_argument("--tag", default="obs", help="short label included in the id")
    parser.add_argument("--id", default=None, help="explicit observation id")
    parser.add_argument("--serial", default=None, help="adb serial (default: only device)")
    parser.add_argument("--adb", default=None, help="path to adb")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--no-notifications",
        action="store_true",
        help="skip `dumpsys notification` (faster, no notification labels)",
    )
    args = parser.parse_args(argv)

    adb = Adb(serial=args.serial, adb_path=args.adb, timeout=args.timeout)
    observation_id = args.id or (
        f"obs_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{args.tag}"
    )
    root = Path(args.out) / observation_id
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    try:
        adb.shell("uiautomator dump /sdcard/provguard_ui.xml")
        adb.pull("/sdcard/provguard_ui.xml", raw / "ui.xml")
        adb.screencap("/sdcard/provguard_screen.png")
        adb.pull("/sdcard/provguard_screen.png", raw / "screen.png")
        (raw / "windows.txt").write_text(
            adb.shell("dumpsys window windows"), encoding="utf-8"
        )
        if not args.no_notifications:
            (raw / "notifications.txt").write_text(
                adb.shell("dumpsys notification --noredact"), encoding="utf-8"
            )
        display = adb.screen_size()
    except AdbError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    files = {
        name: {"path": name, "sha256": sha256_file(raw / name), "bytes": (raw / name).stat().st_size}
        for name in ("ui.xml", "windows.txt", "screen.png")
        if (raw / name).exists()
    }
    if (raw / "notifications.txt").exists():
        files["notifications.txt"] = {
            "path": "notifications.txt",
            "sha256": sha256_file(raw / "notifications.txt"),
            "bytes": (raw / "notifications.txt").stat().st_size,
        }

    meta = {
        "observation_id": observation_id,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "adb_serial": adb.serial or "default",
        "display": None if display is None else {"width": display[0], "height": display[1]},
        "device": _device_metadata(adb),
        "files": files,
        "commands": [
            "uiautomator dump /sdcard/provguard_ui.xml",
            "screencap -p /sdcard/provguard_screen.png",
            "dumpsys window windows",
            *([] if args.no_notifications else ["dumpsys notification --noredact"]),
        ],
    }
    write_json(root / "meta.json", meta)
    print(json.dumps({"observation_id": observation_id, "path": str(root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
