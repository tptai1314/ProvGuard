#!/usr/bin/env python3
"""Anchor-verified, idempotent AOSP hook patcher for ProvGuard.

Supports:
  --check   : Verify every hook anchor exists in --aosp-root without modifying files.
  --apply   : Copy overlay files (optional via --overlay-dir) and inject guarded hook blocks.
  --revert  : Cleanly strip all BEGIN/END PROVGUARD_HOOK blocks from --aosp-root.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


def _markers(hook_id: str, style: str) -> tuple[str, str]:
    prefix = "#" if style == "hash" else "//"
    return (
        f"{prefix} BEGIN PROVGUARD_HOOK:{hook_id}",
        f"{prefix} END PROVGUARD_HOOK:{hook_id}",
    )


def apply_hook_to_text(text: str, hook: dict[str, Any]) -> tuple[str, str]:
    """Return (new_text, status) where status in {'applied', 'already_present', 'anchor_missing'}."""

    hid = str(hook["id"])
    style = str(hook.get("comment_style", "java"))
    begin, end = _markers(hid, style)
    if begin in text and end in text:
        return text, "already_present"

    block = f"\n{begin}\n{hook['snippet']}\n{end}\n"
    mode = str(hook.get("mode", "after"))
    if mode == "append":
        sep = "" if text.endswith("\n") else "\n"
        return text + sep + block.lstrip("\n"), "applied"

    anchor = str(hook["anchor_regex"])
    match = re.search(anchor, text, flags=re.MULTILINE)
    if not match:
        return text, "anchor_missing"

    if mode == "before":
        idx = match.start()
        return text[:idx] + block + text[idx:], "applied"
    idx = match.end()
    return text[:idx] + block + text[idx:], "applied"


def revert_hook_from_text(text: str, hook: dict[str, Any]) -> tuple[str, bool]:
    hid = str(hook["id"])
    style = str(hook.get("comment_style", "java"))
    begin, end = _markers(hid, style)
    pattern = re.compile(
        r"\n?" + re.escape(begin) + r".*?" + re.escape(end) + r"\n?",
        flags=re.DOTALL,
    )
    new_text, count = pattern.subn("\n", text)
    return new_text, count > 0


def copy_overlay(overlay_dir: Path, aosp_root: Path) -> list[str]:
    copied: list[str] = []
    for src in sorted(overlay_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(overlay_dir)
        dst = aosp_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel))
    return copied


def run(
    aosp_root: Path,
    manifest_path: Path,
    *,
    mode: str,
    overlay_dir: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    copied_files: list[str] = []
    if mode == "apply" and overlay_dir is not None and overlay_dir.exists():
        copied_files = copy_overlay(overlay_dir, aosp_root)

    for hook in manifest["hooks"]:
        target = aosp_root / hook["file"]
        if not target.exists():
            results.append({"id": hook["id"], "file": hook["file"], "status": "file_missing"})
            errors.append(f"Missing target file: {hook['file']}")
            continue

        original = target.read_text(encoding="utf-8")
        if mode == "revert":
            updated, removed = revert_hook_from_text(original, hook)
            if removed:
                target.write_text(updated, encoding="utf-8")
            results.append(
                {"id": hook["id"], "file": hook["file"], "status": "reverted" if removed else "not_present"}
            )
            continue

        updated, status = apply_hook_to_text(original, hook)
        results.append({"id": hook["id"], "file": hook["file"], "status": status})
        if status == "anchor_missing":
            errors.append(f"Anchor not found for hook {hook['id']} in {hook['file']}")
        elif mode == "apply" and status == "applied":
            target.write_text(updated, encoding="utf-8")

    return {
        "aosp_root": str(aosp_root),
        "mode": mode,
        "target_branch": manifest.get("aosp_target_branch"),
        "overlay_copied": len(copied_files),
        "hooks": results,
        "errors": errors,
        "passed": len(errors) == 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp-root", required=True, help="Path to synced AOSP root directory")
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).with_name("hooks_manifest.json")),
        help="Path to hooks_manifest.json",
    )
    parser.add_argument(
        "--overlay-dir",
        default=str(Path(__file__).resolve().parents[1] / "overlay"),
        help="Path to aosp/overlay directory",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--revert", action="store_true")
    args = parser.parse_args(argv)

    mode = "check" if args.check else ("apply" if args.apply else "revert")
    report = run(
        Path(args.aosp_root),
        Path(args.manifest),
        mode=mode,
        overlay_dir=Path(args.overlay_dir),
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
