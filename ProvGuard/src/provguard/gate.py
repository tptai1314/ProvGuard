"""Causal Gate (paper Algorithm 2) with masked re-execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .actions import actions_equivalent
from .masking import trusted_projection, untrusted_region_ids
from .schemas import (
    Action,
    EquivalenceMode,
    GateDecision,
    GateResult,
    Transcript,
)
from .sinks import SinkClassifier

DecisionCallback = Callable[[Transcript], Action]


@dataclass(frozen=True)
class CausalGate:
    sink_classifier: SinkClassifier
    trials: int = 1
    threshold: float = 0.5
    equivalence: EquivalenceMode = EquivalenceMode.CONTROL
    attribution_cutoff: float | None = None

    def __post_init__(self) -> None:
        if self.trials < 1:
            raise ValueError("trials must be at least one")
        if not 0 < self.threshold <= 1:
            raise ValueError("threshold must be in (0,1]")

    def evaluate(
        self,
        proposed: Action,
        transcript: Transcript,
        callback: DecisionCallback,
        *,
        attribution_score: float | None = None,
    ) -> tuple[Action, GateResult]:
        """Run Algorithm 2 and return the classified action and auditable result."""

        observation = transcript.observation(proposed.observation_id)
        action = self.sink_classifier.classify(proposed, observation)
        if action.sink_class is None:
            return action, GateResult(
                GateDecision.PASS,
                False,
                None,
                0,
                0,
                (),
                "unprotected action; gate bypassed",
            )
        clearance = self.sink_classifier.clearance(action)
        region_ids = untrusted_region_ids(transcript, clearance)
        if (
            self.attribution_cutoff is not None
            and attribution_score is not None
            and attribution_score >= self.attribution_cutoff
        ):
            return action, GateResult(
                GateDecision.ESCALATE,
                True,
                0.0,
                0,
                self.trials,
                tuple(sorted(region_ids)),
                "high attribution score; conservative early escalation",
            )
        projection = trusted_projection(transcript, region_ids)
        masked_current = projection.observation(action.observation_id)
        equivalent = 0
        for _ in range(self.trials):
            try:
                replay = callback(projection)
            except Exception:  # noqa: BLE001, S112 - external callback must fail closed
                continue
            if actions_equivalent(action, replay, masked_current, self.equivalence):
                equivalent += 1
        support = equivalent / self.trials
        decision = GateDecision.PASS if support >= self.threshold else GateDecision.ESCALATE
        return action, GateResult(
            decision,
            True,
            support,
            equivalent,
            self.trials,
            tuple(sorted(region_ids)),
            "empirical trusted support meets threshold"
            if decision == GateDecision.PASS
            else "empirical trusted support below threshold",
        )
