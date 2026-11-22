#!/usr/bin/env python3
"""Verify dispatch-time binding and execute tap/swipe/type actions via ADB (Tier 3 - C12)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.agent import action_from_dict, action_to_dict
from provguard.binder import DispatchBinder, simulate_live_mutation
from provguard.device import Adb, AdbError
from provguard.dispatch import ActionDispatcher
from provguard.observation import load_observation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observed labels.json or directory")
    parser.add_argument("--action", required=True, help="JSON action to dispatch")
    parser.add_argument(
        "--live-obs",
        default=None,
        help="optional dispatch-time labels.json (if omitted, re-observes via adb or uses --obs in --dry-run)",
    )
    parser.add_argument("--serial", default=None, help="adb device serial")
    parser.add_argument("--adb", default=None, help="path to adb binary")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="verify binding and plan adb commands without sending to a live device",
    )
    parser.add_argument(
        "--no-binder",
        action="store_true",
        help="skip pre-dispatch binding check (for B0 / PG-G ablations)",
    )
    parser.add_argument(
        "--simulate-mutation",
        default="none",
        choices=("none", "digest", "token", "uid", "overlay"),
        help="simulate a UI mutation before dispatch",
    )
    args = parser.parse_args(argv)

    try:
        observed = load_observation(args.obs)
        action = action_from_dict(
            json.loads(args.action),
            default_observation_id=observed.observation_id,
        )
        live_obs = load_observation(args.live_obs) if args.live_obs else None
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.simulate_mutation != "none":
        base_live = live_obs if live_obs is not None else observed
        live_obs = simulate_live_mutation(
            base_live,
            args.simulate_mutation,
            target_region_id=action.target_region_id,
        )

    adb: Adb | None = None
    if not args.dry_run:
        try:
            adb = Adb(serial=args.serial, adb_path=args.adb)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    dispatcher = ActionDispatcher(
        binder=DispatchBinder(),
        adb=adb,
        dry_run=args.dry_run,
        verify_binding=not args.no_binder,
    )
    try:
        record = dispatcher.execute(
            action,
            observed,
            live_observation=live_obs,
        )
    except (AdbError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = {
        "observation_id": observed.observation_id,
        "action": action_to_dict(action),
        "binder_enabled": not args.no_binder,
        "dry_run": args.dry_run,
        **record.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
