#!/usr/bin/env python3
"""Run one agent step (observe -> decide -> parse action) on an observation (Tier 2 - C8)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provguard.agent import ActionParseError, PromptAgentAdapter, action_to_dict
from provguard.model import ModelConfig, ModelError, create_model_client
from provguard.observation import load_observation
from provguard.prompt import PromptMode
from provguard.schemas import Transcript
from provguard.sinks import SinkClassifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observation directory or labels.json path")
    parser.add_argument("--task", required=True, help="authenticated user task")
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
    parser.add_argument("--image", default=None, help="optional screenshot PNG path")
    parser.add_argument("--sinks", default=None, help="optional sinks.yaml path")
    args = parser.parse_args(argv)

    try:
        observation = load_observation(args.obs)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    client = create_model_client(
        ModelConfig(provider=args.provider, model_name=args.model, temperature=0.0)
    )
    screenshots: dict[str, bytes] = {}
    if args.image:
        screenshots[observation.observation_id] = Path(args.image).read_bytes()

    adapter = PromptAgentAdapter(
        model_client=client,
        prompt_mode=PromptMode(args.mode),
        screenshots_by_obs=screenshots,
    )
    transcript = Transcript(task=args.task, observations=(observation,))
    try:
        action = adapter.decide(transcript)
    except (ModelError, ActionParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    classifier = SinkClassifier.from_yaml(args.sinks) if args.sinks else SinkClassifier()
    classified = classifier.classify(action, observation)

    output = {
        "observation_id": observation.observation_id,
        "task": args.task,
        "agent": adapter.identity(),
        "action": action_to_dict(classified),
        "usage": client.tracker.to_dict(),
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
