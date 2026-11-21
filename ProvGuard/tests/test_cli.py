from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return env


def test_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "provguard.cli", "--help"],
        cwd=ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "ProvGuard" in result.stdout


def test_cli_demo(tmp_path: Path) -> None:
    config = tmp_path / "demo.yaml"
    config.write_text(
        "seed: 1\nmode: synthetic\noutput_dir: "
        + str(tmp_path / "out")
        + "\nrepetitions: 1\ngate:\n  trials: 1\n  threshold: 0.5\n  equivalence: control\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "provguard.cli", "demo", "--config", str(config)],
        cwd=ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out" / "results.json").is_file()
    assert (tmp_path / "out" / "attack_success_by_channel.png").is_file()

