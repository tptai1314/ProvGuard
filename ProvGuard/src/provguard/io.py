"""Safe JSON/JSONL output and run provenance."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_json(path: str | Path, value: Any) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    destination.write_text(text, encoding="utf-8")
    return destination


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_metadata(config_path: str | Path, seed: int, *, synthetic: bool) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seed": seed,
        "config_path": str(Path(config_path)),
        "config_sha256": sha256_file(config_path),
        "result_kind": (
            "synthetic smoke-test output, not a paper result" if synthetic else "real experiment"
        ),
    }
