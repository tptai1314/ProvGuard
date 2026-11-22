#!/usr/bin/env python3
"""Verify dispatch-time window token and node digest binding (Tier 3 - C13)."""

from __future__ import annotations

import argparse
import json
import sys

from provguard.actions import resolve_target
from provguard.agent import action_from_dict, action_to_dict
from provguard.binder import (
    DispatchBinder,
    capture_live_observation,
    live_windows_from_observation,
    simulate_live_mutation,
)
from provguard.device import Adb, AdbError
from provguard.observation import load_observation
from provguard.schemas import DispatchStatus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obs", required=True, help="observed labels.json or directory")
    parser.add_argument("--action", required=True, help="JSON action to verify")
    parser.add_argument(
        "--live-obs",
        default=None,
        help="dispatch-time labels.json or directory (default: same as --obs)",
    )
    parser.add_argument(
        "--reobserve",
        action="store_true",
        help="capture fresh dispatch-time state from live device via adb",
    )
    parser.add_argument("--serial", default=None, help="adb device serial for --reobserve")
    parser.add_argument("--adb", default=None, help="path to adb binary")
    parser.add_argument(
        "--simulate-mutation",
        default="none",
        choices=("none", "digest", "token", "uid", "overlay"),
        help="simulate a UI desync/rebinding mutation on the live state",
    )
    parser.add_argument("--no-token-check", action="store_true")
    parser.add_argument("--no-digest-check", action="store_true")
    args = parser.parse_args(argv)

    try:
        observed = load_observation(args.obs)
        action = action_from_dict(
            json.loads(args.action),
            default_observation_id=observed.observation_id,
        )
        if args.reobserve:
            adb = Adb(serial=args.serial, adb_path=args.adb)
            live_obs = capture_live_observation(adb, step=observed.step)
        elif args.live_obs:
            live_obs = load_observation(args.live_obs)
        else:
            live_obs = observed
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError, AdbError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    target = resolve_target(action, observed)
    target_id = target.region_id if target is not None else action.target_region_id
    if args.simulate_mutation != "none":
        live_obs = simulate_live_mutation(
            live_obs,
            args.simulate_mutation,
            target_region_id=target_id,
        )

    binder = DispatchBinder(
        verify_window_token=not args.no_token_check,
        verify_node_digest=not args.no_digest_check,
    )
    live_windows = live_windows_from_observation(live_obs)
    result = binder.dispatch(action, observed, live_windows)

    binding_info = None
    if target is not None and target.binding is not None:
        binding_info = {
            "window_token": target.binding.window_token,
            "node_id": target.binding.node_id,
            "digest": target.binding.digest,
            "owner_uid": target.binding.owner_uid,
        }

    payload = {
        "observation_id": observed.observation_id,
        "live_observation_id": live_obs.observation_id,
        "action": action_to_dict(action),
        "target_region_id": target_id,
        "observed_binding": binding_info,
        "simulated_mutation": args.simulate_mutation,
        "status": result.status.value,
        "reobserve_required": result.status == DispatchStatus.REOBSERVE,
        "window_token": result.window_token,
        "reason": result.reason,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
