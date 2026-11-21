"""Thin, testable wrapper around `adb`.

All device access goes through this module so that the collection scripts never
build shell strings themselves. Binary output (screenshots) is transferred with
`adb pull` instead of stdout redirection, because Windows PowerShell corrupts binary
pipes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class AdbError(RuntimeError):
    """Raised when an adb command fails."""


def find_adb(explicit: str | Path | None = None) -> str:
    """Locate adb: explicit path, $ADB, PATH, then the standard Android SDK path."""

    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env_value = os.environ.get("ADB")
    if env_value:
        candidates.append(Path(env_value))
    which = shutil.which("adb")
    if which:
        candidates.append(Path(which))
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Android" / "Sdk" / "platform-tools" / "adb.exe")
        candidates.append(Path(local_appdata) / "Android" / "Sdk" / "platform-tools" / "adb")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "adb not found. Install Android platform-tools or set the ADB environment variable."
    )


class Adb:
    def __init__(
        self,
        serial: str | None = None,
        adb_path: str | Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.adb_path = find_adb(adb_path)
        self.serial = serial
        self.timeout = timeout

    def _command(self, args: list[str]) -> list[str]:
        command = [self.adb_path]
        if self.serial:
            command += ["-s", self.serial]
        return command + args

    def run(
        self,
        args: list[str],
        *,
        timeout: float | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                self._command(args),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout if timeout is not None else self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"adb {' '.join(args)} timed out after {exc.timeout}s") from exc
        if check and completed.returncode != 0:
            raise AdbError(
                f"adb {' '.join(args)} failed ({completed.returncode}): "
                f"{(completed.stderr or completed.stdout).strip()}"
            )
        return completed

    def shell(self, command: str, *, timeout: float | None = None) -> str:
        return self.run(["shell", command], timeout=timeout).stdout

    def pull(self, remote: str, local: str | Path) -> Path:
        destination = Path(local)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.run(["pull", remote, str(destination)])
        if not destination.exists():
            raise AdbError(f"adb pull reported success but {destination} does not exist")
        return destination

    def devices(self) -> list[str]:
        output = self.run(["devices"]).stdout
        serials: list[str] = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        return serials

    def getprop(self, name: str) -> str:
        return self.shell(f"getprop {name}").strip()

    def screencap(self, remote: str = "/sdcard/provguard_screen.png") -> None:
        self.shell(f"screencap -p {remote}", timeout=max(self.timeout, 30.0))

    def screen_size(self) -> tuple[int, int] | None:
        output = self.shell("wm size").strip()
        for line in output.splitlines():
            if "Physical size:" in line:
                dimensions = line.split("Physical size:")[1].strip()
                width, _, height = dimensions.partition("x")
                if width.isdigit() and height.isdigit():
                    return int(width), int(height)
        return None
