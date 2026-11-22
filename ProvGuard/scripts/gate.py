#!/usr/bin/env python3
"""Causal Gate runner wrapping provguard.gate.CausalGate with live/heuristic callbacks (Tier 2 - C10)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from provguard.agent import PromptAgentAdapter, action_from_dict, action_to_dict
from provguard.gate import CausalGate
from provguard.model import ModelConfig, create_model_client
from provguard.observation import load_observation, observation_from_dict
from provguard.prompt import PromptMode
from provguard.schemas import EquivalenceMode, GateDecision, Observation, Transcript
from provguard.sinks import SinkClassifier


def _load_case(
    case_path: str | Path,
) -> tuple[str, Observation, dict[str, Any] | None, str | None]:
    raw = json.loads(Path(case_path).read_text(encoding="utf-8"))
    task = str(raw["task"])
    obs_data = raw.get("observation", raw)
    observation = observation_from_dict(obs_data)
    proposed_dict = raw.get("proposed_action")
    expected = raw.get("expected_decision")
    return task, observation, proposed_dict, expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=None, help="JSON case file (task + observation + action)")
    parser.add_argument("--obs", default=None, help="observation directory or labels.json path")
    parser.add_argument("--task", default=None, help="authenticated user task (when using --obs)")
    parser.add_argument("--action", default=None, help="explicit JSON action (optional)")
    parser.add_argument(
        "--provider",
        default="heuristic",
        choices=("heuristic", "gemini", "openai", "ollama"),
    )
    parser.add_argument("--model", default="heuristic-v1")
    parser.add_argument(
        "--mode",
        default="plain",
        choices=("plain", "labeled", "spotlighting"),
    )
    parser.add_argument("--trials", "-k", type=int, default=5, help="re-execution trials k")
    parser.add_argument("--threshold", "--theta", type=float, default=0.5, help="support threshold")
    parser.add_argument(
        "--equivalence",
        default="control",
        choices=("control", "strict"),
    )
    parser.add_argument("--sinks", default=None, help="optional sinks.yaml path")
    args = parser.parse_args(argv)

    if not args.case and not (args.obs and args.task):
        print("error: provide either --case <case.json> or both --obs and --task", file=sys.stderr)
        return 2

    try:
        if args.case:
            task, observation, proposed_raw, expected = _load_case(args.case)
        else:
            task = str(args.task)
            observation = load_observation(args.obs)
            proposed_raw = json.loads(args.action) if args.action else None
            expected = None
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    provider = args.provider
    if provider == "heuristic" and args.model.startswith("gpt-"):
        # Allow `--model gpt-4o-mini` offline without API key unless --provider openai is explicit
        provider = "heuristic"

    client = create_model_client(
        ModelConfig(provider=provider, model_name=args.model, temperature=0.0)
    )
    adapter = PromptAgentAdapter(
        model_client=client,
        prompt_mode=PromptMode(args.mode),
    )
    transcript = Transcript(task=task, observations=(observation,))

    if proposed_raw is not None:
        proposed = action_from_dict(proposed_raw, default_observation_id=observation.observation_id)
    else:
        proposed = adapter.decide(transcript)

    classifier = SinkClassifier.from_yaml(args.sinks) if args.sinks else SinkClassifier()
    gate = CausalGate(
        sink_classifier=classifier,
        trials=args.trials if classified_needs_trials(classifier, proposed, observation) else 1,
        threshold=args.threshold,
        equivalence=EquivalenceMode(args.equivalence),
    )
    # Use configured k trials for the gate instance
    gate = CausalGate(
        sink_classifier=classifier,
        trials=args.trials,
        threshold=args.threshold,
        equivalence=EquivalenceMode(args.equivalence),
    )
    classified_action, result = gate.evaluate(proposed, transcript, adapter.decide)
    verdict = "pass" if result.decision == GateDecision.PASS else "block"

    payload: dict[str, Any] = {
        "observation_id": observation.observation_id,
        "task": task,
        "proposed_action": action_to_dict(classified_action),
        "protected": result.protected,
        "sink_class": classified_action.sink_class.value if classified_action.sink_class else None,
        "decision": result.decision.value,
        "verdict": verdict,
        "support_fraction": result.support_fraction,
        "equivalent_trials": result.equivalent_trials,
        "trials": result.trials,
        "untrusted_region_ids": list(result.untrusted_region_ids),
        "reason": result.reason,
        "usage": client.tracker.to_dict(),
    }
    if expected is not None:
        payload["expected_verdict"] = expected
        payload["matches_expected"] = verdict == expected or result.decision.value == expected

    print(json.dumps(payload, indent=2))
    return 0


def classified_needs_trials(
    classifier: SinkClassifier, proposed: Any, observation: Observation
) -> bool:
    return classifier.classify(proposed, observation).sink_class is not None


if __name__ == "__main__":
    raise SystemExit(main())
