"""Composition of Observe/Gate/Endorse/Dispatch from paper Algorithm 4."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .binder import DispatchBinder
from .gate import CausalGate, DecisionCallback
from .schemas import (
    Action,
    DispatchResult,
    DispatchStatus,
    GateDecision,
    GateResult,
    LiveWindow,
    Transcript,
)

EndorsementCallback = Callable[[Action, GateResult], bool]


@dataclass(frozen=True)
class StepResult:
    action: Action
    gate: GateResult
    dispatch: DispatchResult
    endorsed: bool
    transcript: Transcript


@dataclass
class ProvGuardPipeline:
    gate: CausalGate
    binder: DispatchBinder

    def step(
        self,
        proposed: Action,
        transcript: Transcript,
        callback: DecisionCallback,
        live_windows: tuple[LiveWindow, ...],
        endorsement: EndorsementCallback | None = None,
    ) -> StepResult:
        action, gate_result = self.gate.evaluate(proposed, transcript, callback)
        endorsed = False
        if gate_result.decision == GateDecision.ESCALATE:
            endorsed = endorsement(action, gate_result) if endorsement is not None else False
            if not endorsed:
                return StepResult(
                    action,
                    gate_result,
                    DispatchResult(DispatchStatus.DROPPED, "escalation denied or unavailable"),
                    False,
                    transcript,
                )
        observation = transcript.observation(action.observation_id)
        dispatch_result = self.binder.dispatch(action, observation, live_windows)
        updated = (
            transcript.append_action(action)
            if dispatch_result.status == DispatchStatus.DELIVERED
            else transcript
        )
        return StepResult(action, gate_result, dispatch_result, endorsed, updated)

