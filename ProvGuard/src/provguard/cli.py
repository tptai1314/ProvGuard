"""Command-line interface for reference-model experiments."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .adapters.datasets import JsonlTrialAdapter
from .config import load_config
from .experiments.runner import ablate, calibrate, evaluate
from .io import run_metadata, write_json
from .plotting import plot_results

LOGGER = logging.getLogger("provguard")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProvGuard reference model and evaluation harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("demo", "calibrate", "evaluate", "ablate"):
        item = subparsers.add_parser(command)
        item.add_argument("--config", required=True)
    plot = subparsers.add_parser("plot")
    plot.add_argument("--input", required=True)
    plot.add_argument("--output", required=True)
    validate = subparsers.add_parser("validate-data")
    validate.add_argument("--root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parser().parse_args(argv)
    if args.command == "plot":
        paths = plot_results(args.input, args.output)
        LOGGER.info("Wrote %s", ", ".join(map(str, paths)))
        return 0
    if args.command == "validate-data":
        rows = JsonlTrialAdapter().load(args.root)
        LOGGER.info("Validated %d local trial records", len(rows))
        return 0
    config = load_config(args.config)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "run_metadata.json",
        run_metadata(args.config, config.seed, synthetic=config.mode == "synthetic"),
    )
    if args.command == "calibrate":
        result = calibrate(config, output_dir)
    elif args.command == "evaluate":
        result = evaluate(config, output_dir)
    elif args.command == "ablate":
        result = ablate(config, output_dir)
    else:
        calibration = calibrate(config, output_dir)
        evaluation = evaluate(config, output_dir)
        ablation = ablate(config, output_dir)
        paths = plot_results(output_dir / "results.json", output_dir)
        result = {
            "calibration": calibration,
            "evaluation": evaluation,
            "ablation": ablation,
            "plots": [str(path) for path in paths],
        }
    LOGGER.info("%s", json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

