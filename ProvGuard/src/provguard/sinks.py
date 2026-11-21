"""Deterministic reference sink classifier and Table 4 clearances."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .actions import resolve_target
from .lattice import IntegrityLabel, leq
from .schemas import Action, ActionOp, Observation, SinkClass

DEFAULT_CLEARANCES: dict[SinkClass, IntegrityLabel] = {
    SinkClass.GRANT: IntegrityLabel.SYSTEM,
    SinkClass.INSTALL: IntegrityLabel.SYSTEM,
    SinkClass.SHARE: IntegrityLabel.APP,
    SinkClass.SEND: IntegrityLabel.APP,
    SinkClass.PAY: IntegrityLabel.APP,
    SinkClass.DELETE: IntegrityLabel.APP,
    SinkClass.TYPE_UNTRUSTED: IntegrityLabel.APP,
}


@dataclass(frozen=True)
class SinkClassifier:
    """Classify OS sinks exactly and app sinks through configurable role/id rules."""

    clearances: dict[SinkClass, IntegrityLabel] = field(
        default_factory=lambda: dict(DEFAULT_CLEARANCES)
    )
    app_role_rules: dict[str, SinkClass] = field(
        default_factory=lambda: {
            "send": SinkClass.SEND,
            "payment_confirm": SinkClass.PAY,
            "delete_confirm": SinkClass.DELETE,
        }
    )

    def classify(self, action: Action, observation: Observation) -> Action:
        if action.sink_class is not None:
            return action
        target = resolve_target(action, observation)
        if action.op == ActionOp.TYPE and target is not None and not leq(
            target.label, IntegrityLabel.APP
        ):
            return replace(action, sink_class=SinkClass.TYPE_UNTRUSTED)
        if target is None:
            return action
        role = str(target.metadata.get("semantic_role", ""))
        system_sink = target.metadata.get("system_sink")
        if system_sink in {SinkClass.GRANT.value, SinkClass.INSTALL.value, SinkClass.SHARE.value}:
            return replace(action, sink_class=SinkClass(system_sink))
        if role in self.app_role_rules:
            return replace(action, sink_class=self.app_role_rules[role])
        return action

    def clearance(self, action: Action) -> IntegrityLabel:
        if action.sink_class is None:
            raise ValueError("Unprotected action has no clearance")
        try:
            return self.clearances[action.sink_class]
        except KeyError as exc:
            raise ValueError(f"No clearance configured for {action.sink_class.value}") from exc

