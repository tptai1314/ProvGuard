"""Unit and integration tests for Tier 3 control modules (C12 dispatch.py & C13 binder.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provguard.binder import (
    DispatchBinder,
    live_windows_from_observation,
    simulate_live_mutation,
)
from provguard.dispatch import (
    ActionDispatcher,
    escape_adb_input_text,
    plan_adb_commands,
    resolve_action_point,
)
from provguard.observation import observation_from_dict
from provguard.schemas import Action, ActionOp, DispatchStatus

CASES_DIR = Path(__file__).parent / "cases"


class _FakeAdb:
    """In-memory ADB stub recording executed shell commands."""

    def __init__(self) -> None:
        self.commands: list[str] = []

    def shell(self, command: str, *, timeout: float | None = None) -> str:
        self.commands.append(command)
        return ""


def _load_case02_observation():
    raw = json.loads((CASES_DIR / "case02.json").read_text(encoding="utf-8"))
    return observation_from_dict(raw["observation"])


def test_live_windows_from_observation_preserves_tokens_and_digests() -> None:
    obs = _load_case02_observation()
    windows = live_windows_from_observation(obs)
    assert len(windows) == 1
    win = windows[0]
    assert win.token == "win_messages"
    assert win.owner_uid == 10150
    assert win.nodes["0.2:send_message_button"] == "b1b2c3d4e5f60002"
    assert win.nodes["r0.2"] == "b1b2c3d4e5f60002"
    assert win.touchable_at(940, 1670) is True


@pytest.mark.parametrize(
    ("mutation", "expected_status", "expected_reason_substr"),
    [
        ("none", DispatchStatus.DELIVERED, "binding matched"),
        ("digest", DispatchStatus.REOBSERVE, "node identity or digest changed"),
        ("token", DispatchStatus.REOBSERVE, "observed window no longer exists"),
        ("uid", DispatchStatus.REOBSERVE, "window owner changed"),
        ("overlay", DispatchStatus.REOBSERVE, "not topmost touchable target"),
    ],
)
def test_binder_detects_all_four_rebinding_mutations(
    mutation: str,
    expected_status: DispatchStatus,
    expected_reason_substr: str,
) -> None:
    observed = _load_case02_observation()
    action = Action(op=ActionOp.TAP, observation_id=observed.observation_id, target_region_id="r0.2")
    live_obs = simulate_live_mutation(observed, mutation, target_region_id="r0.2")

    result = DispatchBinder().verify_against_observation(action, observed, live_obs)
    assert result.status == expected_status
    assert expected_reason_substr in result.reason


def test_plan_adb_commands_for_all_action_ops() -> None:
    obs = _load_case02_observation()

    # 1. TAP on r0.2 ([840, 1600, 1040, 1740] -> center 940, 1670)
    tap = Action(op=ActionOp.TAP, observation_id=obs.observation_id, target_region_id="r0.2")
    assert resolve_action_point(tap, obs) == (940, 1670)
    assert plan_adb_commands(tap, obs) == ["input tap 940 1670"]

    # 2. LONG_PRESS on r0.2
    lp = Action(op=ActionOp.LONG_PRESS, observation_id=obs.observation_id, target_region_id="r0.2")
    assert plan_adb_commands(lp, obs) == ["input swipe 940 1670 940 1670 800"]

    # 3. TYPE into r0.1 ([40, 1600, 820, 1740] -> center 430, 1670)
    type_act = Action(
        op=ActionOp.TYPE,
        observation_id=obs.observation_id,
        target_region_id="r0.1",
        argument="Hello Alice!",
    )
    assert plan_adb_commands(type_act, obs) == [
        "input tap 430 1670",
        'input text "Hello%sAlice!"',
    ]
    assert escape_adb_input_text('a b$c"d') == 'a%sb\\$c\\"d'

    # 4. SWIPE directional and explicit coordinates
    swipe_up = Action(op=ActionOp.SWIPE, observation_id=obs.observation_id, argument="up")
    cmds_up = plan_adb_commands(swipe_up, obs)
    assert len(cmds_up) == 1 and cmds_up[0].startswith("input swipe 540 ")

    swipe_coords = Action(
        op=ActionOp.SWIPE,
        observation_id=obs.observation_id,
        argument="100,1800,100,400,250",
    )
    assert plan_adb_commands(swipe_coords, obs) == ["input swipe 100 1800 100 400 250"]

    # 5. BACK, HOME, LAUNCH, FINISH
    assert plan_adb_commands(Action(op=ActionOp.BACK, observation_id=obs.observation_id), obs) == [
        "input keyevent KEYCODE_BACK"
    ]
    assert plan_adb_commands(Action(op=ActionOp.HOME, observation_id=obs.observation_id), obs) == [
        "input keyevent KEYCODE_HOME"
    ]
    assert plan_adb_commands(
        Action(op=ActionOp.LAUNCH, observation_id=obs.observation_id, argument="com.android.settings"),
        obs,
    ) == ["monkey -p com.android.settings -c android.intent.category.LAUNCHER 1"]
    assert plan_adb_commands(Action(op=ActionOp.FINISH, observation_id=obs.observation_id), obs) == []

    with pytest.raises(ValueError, match="valid package name"):
        plan_adb_commands(
            Action(op=ActionOp.LAUNCH, observation_id=obs.observation_id, argument="bad;rm -rf"),
            obs,
        )


def test_action_dispatcher_executes_when_binding_matches_and_aborts_on_mismatch() -> None:
    obs = _load_case02_observation()
    action = Action(op=ActionOp.TAP, observation_id=obs.observation_id, target_region_id="r0.2")

    # 1. Matching binding -> sends command to ADB
    fake_adb = _FakeAdb()
    dispatcher = ActionDispatcher(
        binder=DispatchBinder(),
        adb=fake_adb,  # type: ignore[arg-type]
        dry_run=False,
        verify_binding=True,
    )
    rec_ok = dispatcher.execute(action, obs, live_observation=obs)
    assert rec_ok.status == DispatchStatus.DELIVERED
    assert rec_ok.executed is True
    assert fake_adb.commands == ["input tap 940 1670"]

    # 2. Mutated digest before dispatch -> aborts before sending any ADB command
    fake_adb_blocked = _FakeAdb()
    dispatcher_blocked = ActionDispatcher(
        binder=DispatchBinder(),
        adb=fake_adb_blocked,  # type: ignore[arg-type]
        dry_run=False,
        verify_binding=True,
    )
    mutated_live = simulate_live_mutation(obs, "digest", target_region_id="r0.2")
    rec_blocked = dispatcher_blocked.execute(action, obs, live_observation=mutated_live)
    assert rec_blocked.status == DispatchStatus.REOBSERVE
    assert rec_blocked.executed is False
    assert rec_blocked.commands == ()
    assert fake_adb_blocked.commands == []
