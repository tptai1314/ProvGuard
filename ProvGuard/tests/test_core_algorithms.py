from provguard.binder import DispatchBinder
from provguard.gate import CausalGate
from provguard.masking import MASK_PLACEHOLDER, trusted_projection, untrusted_region_ids
from provguard.schemas import (
    Action,
    ActionOp,
    DispatchStatus,
    EquivalenceMode,
    GateDecision,
    SinkClass,
)
from provguard.sinks import SinkClassifier
from provguard.synthetic import build_scenarios


def test_untrusted_content_is_masked_but_geometry_is_preserved() -> None:
    scenario = next(s for s in build_scenarios() if s.channel == "webview")
    ids = untrusted_region_ids(scenario.transcript, SinkClassifier().clearances[SinkClass.SEND])
    projected = trusted_projection(scenario.transcript, ids)
    original = scenario.transcript.observations[0].regions[-1]
    masked = projected.observations[0].regions[-1]
    assert masked.content == MASK_PLACEHOLDER
    assert masked.geometry == original.geometry


def test_gate_escalates_injected_action_and_passes_benign_action() -> None:
    gate = CausalGate(SinkClassifier(), 1, 0.5, EquivalenceMode.CONTROL)
    attack = next(s for s in build_scenarios() if s.channel == "sdk_runtime_ads")
    benign = next(s for s in build_scenarios() if s.trial_type == "benign")

    def callback_for(scenario):
        def callback(transcript):
            visible = any("EXFILTRATE" in r.content for o in transcript.observations for r in o.regions)
            return scenario.proposed if visible or scenario.trial_type == "benign" else Action(
                ActionOp.BACK, scenario.proposed.observation_id
            )

        return callback

    _, attack_result = gate.evaluate(attack.proposed, attack.transcript, callback_for(attack))
    _, benign_result = gate.evaluate(benign.proposed, benign.transcript, callback_for(benign))
    assert attack_result.decision == GateDecision.ESCALATE
    assert benign_result.decision == GateDecision.PASS


def test_dispatch_binder_rejects_foreground_rebinding() -> None:
    scenario = next(s for s in build_scenarios() if s.channel == "foreground_rebinding")
    result = DispatchBinder().dispatch(
        scenario.proposed, scenario.transcript.observations[0], scenario.live_windows
    )
    assert result.status == DispatchStatus.REOBSERVE

