"""Local-file-only dataset adapters. No adapter downloads data."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

REQUIRED_TRIAL_FIELDS = {
    "trial_id",
    "suite",
    "channel",
    "trial_type",
    "ground_truth_protected",
}


class DatasetAdapter(ABC):
    @abstractmethod
    def load(self, root: str | Path) -> list[dict[str, Any]]:
        """Load manually provisioned local data; never perform network access."""


class JsonlTrialAdapter(DatasetAdapter):
    filename = "trials.jsonl"

    def load(self, root: str | Path) -> list[dict[str, Any]]:
        path = Path(root) / self.filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Expected {path}. Provision the benchmark manually; automatic download is disabled."
            )
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = REQUIRED_TRIAL_FIELDS - row.keys()
            if missing:
                raise ValueError(f"{path}:{line_number}: missing fields {sorted(missing)}")
            rows.append(row)
        return rows


class ExternalBenchmarkAdapter(JsonlTrialAdapter):
    """Named stub for a published suite after its artifact has been normalized to JSONL."""

    suite_name: str = "external"


class AgentHazardAdapter(ExternalBenchmarkAdapter):
    suite_name = "AgentHazard"


class MobileWorldSafetyAdapter(ExternalBenchmarkAdapter):
    suite_name = "MobileWorldSafety"


class GhostEIBenchAdapter(ExternalBenchmarkAdapter):
    suite_name = "GhostEI-Bench"


class NotAnA11yAdapter(ExternalBenchmarkAdapter):
    suite_name = "Not-an-A11y"


class UIDesyncAdapter(ExternalBenchmarkAdapter):
    suite_name = "UI-desync"


class ChannelAttackAdapter(ExternalBenchmarkAdapter):
    suite_name = "channel-attacks"


class ActionRebindingAdapter(ExternalBenchmarkAdapter):
    suite_name = "action-rebinding"


class AndroidWorldAdapter(ExternalBenchmarkAdapter):
    suite_name = "AndroidWorld"


class AndroidLabAdapter(ExternalBenchmarkAdapter):
    suite_name = "AndroidLab"

