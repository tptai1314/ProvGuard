"""Bridge between ProvGuard Python evaluation harness and AOSP `cmd provguard` service.

Enables running the exact same benchmark runners against a live ProvGuard-patched
AOSP Cuttlefish or Android Emulator image over ADB.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ShellRunner = Callable[[list[str]], str]


def _default_adb_runner(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.stdout.strip()


@dataclass(frozen=True)
class AospTelemetry:
    enabled: bool
    aosp_tcb: bool
    gate_evaluated: int
    gate_protected: int
    gate_escalated: int
    binder_delivered: int
    binder_rejected: int


@dataclass(frozen=True)
class OsProvenanceEntry:
    region_id: str
    uid: int
    window_type: int
    label: str
    perceivable: bool
    contrast: float
    visible_fraction: float
    digest: str


class AospProvGuardBridge:
    """Typed wrapper around `adb [-s serial] shell cmd provguard <subcommand>`."""

    def __init__(
        self,
        *,
        serial: str | None = None,
        adb_bin: str = "adb",
        runner: ShellRunner | None = None,
    ) -> None:
        self.serial = serial
        self.adb_bin = adb_bin
        self._runner = runner or _default_adb_runner

    def _cmd(self, *subargs: str) -> str:
        argv = [self.adb_bin]
        if self.serial:
            argv.extend(["-s", self.serial])
        argv.extend(["shell", "cmd", "provguard", *subargs])
        return self._runner(argv)

    def is_available(self) -> bool:
        try:
            tel = self.status()
            return tel.aosp_tcb
        except Exception:  # noqa: BLE001
            return False

    def status(self) -> AospTelemetry:
        raw = self._cmd("status")
        data: dict[str, Any] = json.loads(raw)
        return AospTelemetry(
            enabled=bool(data.get("enabled", False)),
            aosp_tcb=bool(data.get("aosp_tcb", False)),
            gate_evaluated=int(data.get("gate_evaluated", 0)),
            gate_protected=int(data.get("gate_protected", 0)),
            gate_escalated=int(data.get("gate_escalated", 0)),
            binder_delivered=int(data.get("binder_delivered", 0)),
            binder_rejected=int(data.get("binder_rejected", 0)),
        )

    def set_enabled(self, enabled: bool) -> bool:
        raw = self._cmd("enable" if enabled else "disable")
        data: dict[str, Any] = json.loads(raw)
        return bool(data.get("enabled", False))

    def set_task(self, task: str) -> bool:
        raw = self._cmd("set-task", task)
        data: dict[str, Any] = json.loads(raw)
        return bool(data.get("task_set", False))

    def configure_gate(
        self,
        *,
        trials: int = 1,
        theta: float = 0.5,
        strict_equivalence: bool = False,
    ) -> dict[str, Any]:
        raw = self._cmd(
            "config",
            str(trials),
            str(theta),
            "true" if strict_equivalence else "false",
        )
        return dict(json.loads(raw))

    def get_provenance(self) -> list[OsProvenanceEntry]:
        raw = self._cmd("provenance")
        items: list[dict[str, Any]] = json.loads(raw)
        return [
            OsProvenanceEntry(
                region_id=str(it["region_id"]),
                uid=int(it["uid"]),
                window_type=int(it["window_type"]),
                label=str(it["label"]),
                perceivable=bool(it["perceivable"]),
                contrast=float(it["contrast"]),
                visible_fraction=float(it["visible_fraction"]),
                digest=str(it["digest"]),
            )
            for it in items
        ]

    def reset(self) -> bool:
        raw = self._cmd("reset")
        data: dict[str, Any] = json.loads(raw)
        return bool(data.get("reset", False))
