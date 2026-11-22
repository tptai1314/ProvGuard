#!/usr/bin/env python3
"""Scan an observation for protected sinks or classify a candidate action (Tier 2 - C11)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.agent import action_from_dict, action_to_dict
from provguard.observation import load_observation
from provguard.sinks import SinkClassifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observation directory or labels.json path")
    parser.add_argument("--config", default=None, help="optional sinks.yaml path")
    parser.add_argument("--action", default=None, help="optional JSON action to classify")
    args = parser.parse_args(argv)

    try:
        observation = load_observation(args.obs)
        classifier = SinkClassifier.from_yaml(args.config) if args.config else SinkClassifier()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.action:
        action = action_from_dict(
            json.loads(args.action),
            default_observation_id=observation.observation_id,
        )
        classified = classifier.classify(action, observation)
        clearance = (
            classifier.clearance(classified).value
            if classified.sink_class is not None
            else None
        )
        print(
            json.dumps(
                {
                    "action": action_to_dict(classified),
                    "protected": classified.sink_class is not None,
                    "sink_class": classified.sink_class.value if classified.sink_class else None,
                    "required_clearance": clearance,
                },
                indent=2,
            )
        )
        return 0

    detected = classifier.scan_observation(observation)
    payload = {
        "observation_id": observation.observation_id,
        "regions_total": len(observation.regions),
        "sinks_detected": len(detected),
        "sinks": [
            {
                "region_id": region.region_id,
                "sink_class": sink_class.value,
                "required_clearance": classifier.clearances[sink_class].value,
                "rule": rule_name,
                "content": region.content,
                "resource_id": region.metadata.get("resource_id", ""),
                "label": region.label.value,
                "perceivable": region.provenance.perceivable,
            }
            for region, sink_class, rule_name in detected
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
