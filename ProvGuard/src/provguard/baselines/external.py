"""B4 external wrapper; no invented OS-Sentinel API."""

from __future__ import annotations

from ..schemas import Action, Transcript
from .base import Baseline


class OSSentinelAdapter(Baseline):
    name = "B4-OS-Sentinel"

    def allow(self, action: Action, transcript: Transcript) -> bool:
        raise RuntimeError(
            "OS-Sentinel is an external formal-verifier/VLM baseline. Install its pinned artifact "
            "and implement this adapter against the released API; no API is assumed here."
        )

