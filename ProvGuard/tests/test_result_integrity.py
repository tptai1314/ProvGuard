from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_outputs_never_pose_as_paper_results() -> None:
    for path in (ROOT / "outputs").glob("**/*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data).lower()
        assert "synthetic" in text or "analytical calculation" in text

