#!/usr/bin/env python3
from __future__ import annotations

import argparse

from provguard.cli import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(main(["plot", "--input", args.input, "--output", args.output]))

