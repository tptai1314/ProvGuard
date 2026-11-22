"""YAML configuration loading with conservative validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .schemas import EquivalenceMode


@dataclass(frozen=True)
class GateConfig:
    trials: int = 1
    threshold: float = 0.5
    equivalence: EquivalenceMode = EquivalenceMode.CONTROL
    attribution_cutoff: float | None = None


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 2026
    output_dir: str = "outputs/synthetic_demo"
    repetitions: int = 5
    mode: str = "synthetic"
    data_root: str | None = None
    gate: GateConfig = field(default_factory=GateConfig)
    q0: float = 0.2
    q1: float = 0.8
    delta: float = 0.01
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise TypeError("Configuration root must be a mapping")
    gate_data = data.get("gate", {})
    gate = GateConfig(
        trials=int(gate_data.get("trials", 1)),
        threshold=float(gate_data.get("threshold", 0.5)),
        equivalence=EquivalenceMode(gate_data.get("equivalence", "control")),
        attribution_cutoff=(
            None
            if gate_data.get("attribution_cutoff") is None
            else float(gate_data["attribution_cutoff"])
        ),
    )
    if gate.trials < 1 or not 0 < gate.threshold <= 1:
        raise ValueError("Invalid gate trials or threshold")
    mode = str(data.get("mode", "synthetic"))
    if mode not in {"synthetic", "real"}:
        raise ValueError("mode must be 'synthetic' or 'real'")
    repetitions = int(data.get("repetitions", 5))
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    return ExperimentConfig(
        seed=int(data.get("seed", 2026)),
        output_dir=str(data.get("output_dir", "outputs/synthetic_demo")),
        repetitions=repetitions,
        mode=mode,
        data_root=data.get("data", {}).get("root"),
        gate=gate,
        q0=float(data.get("calibration", {}).get("q0", 0.2)),
        q1=float(data.get("calibration", {}).get("q1", 0.8)),
        delta=float(data.get("calibration", {}).get("delta", 0.01)),
        raw=data,
    )
