#!/usr/bin/env python3
"""Unified model client CLI (Tier 2 - C6): retry, token accounting, temperature 0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provguard.model import ModelConfig, ModelError, create_model_client


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        default="heuristic",
        choices=("heuristic", "gemini", "openai", "ollama"),
        help="model provider backend",
    )
    parser.add_argument("--model", default="heuristic-v1", help="model identifier")
    parser.add_argument("--prompt", required=True, help="user prompt string or @path")
    parser.add_argument("--system", default=None, help="optional system instruction")
    parser.add_argument("--image", default=None, help="optional PNG screenshot path")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)

    prompt_text = args.prompt
    if prompt_text.startswith("@"):
        prompt_text = Path(prompt_text[1:]).read_text(encoding="utf-8")

    image_bytes = Path(args.image).read_bytes() if args.image else None
    config = ModelConfig(
        provider=args.provider,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        retry_count=args.retries,
        timeout_sec=args.timeout,
    )
    client = create_model_client(config)
    try:
        response = client.complete(prompt_text, system=args.system, image_png=image_bytes)
    except ModelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = {
        "provider": response.provider,
        "model": response.model,
        "text": response.text,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
        "latency_ms": round(response.latency_ms, 2),
        "tracker": client.tracker.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
