#!/usr/bin/env python3
from __future__ import annotations

import argparse

from provguard.cli import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--stage", choices=["calibrate", "evaluate", "ablate"], required=True)
    args = parser.parse_args()
    raise SystemExit(main([args.stage, "--config", args.config]))

