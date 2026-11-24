"""Tests verifying loaders for the 4 downloaded external benchmarks (Table 6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from provguard.adapters.external_suites import (
    load_agenthazard_cases,
    load_androidworld_benign_cases,
    load_ghostei_cases,
    load_not_an_a11y_cases,
)
from provguard.lattice import IntegrityLabel

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_ROOT = REPO_ROOT / "datasets_external"


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "AgentHazard" / "data" / "data" / "static").exists(),
    reason="AgentHazard dataset not provisioned locally",
)
def test_load_agenthazard_cases_supports_g1_and_strict() -> None:
    g1_cases = load_agenthazard_cases(
        EXTERNAL_ROOT / "AgentHazard" / "data" / "data" / "static",
        limit=6,
        third_party_as_sdk=False,
    )
    strict_cases = load_agenthazard_cases(
        EXTERNAL_ROOT / "AgentHazard" / "data" / "data" / "static",
        limit=6,
        third_party_as_sdk=True,
    )
    assert len(g1_cases) == 6
    assert len(strict_cases) == 6
    assert all(c.suite == "AgentHazard" for c in g1_cases)
    assert any(r.label == IntegrityLabel.SDK for r in strict_cases[0].observation.regions)


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "Ghost-EI" / "datasets" / "GhostEI.jsonl").exists(),
    reason="GhostEI dataset not provisioned locally",
)
def test_load_ghostei_cases_stratified() -> None:
    cases = load_ghostei_cases(
        EXTERNAL_ROOT / "Ghost-EI" / "datasets" / "GhostEI.jsonl",
        per_channel_limit=5,
    )
    assert len(cases) == 15
    assert {c.channel for c in cases} == {
        "ghostei_overlay",
        "ghostei_popup_sms",
        "ghostei_non_script",
    }


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "Not-An-A11y" / "Runtime Injection").exists(),
    reason="Not-An-A11y dataset not provisioned locally",
)
def test_load_not_an_a11y_cases() -> None:
    cases = load_not_an_a11y_cases(EXTERNAL_ROOT / "Not-An-A11y")
    assert len(cases) >= 8
    assert {c.channel for c in cases} >= {"a1_notification", "a3_a4_overlay_web", "a9_appcard"}


@pytest.mark.skipif(
    not (EXTERNAL_ROOT / "android_world" / "android_world" / "task_metadata.json").exists(),
    reason="AndroidWorld metadata not provisioned locally",
)
def test_load_androidworld_benign_cases() -> None:
    cases = load_androidworld_benign_cases(
        EXTERNAL_ROOT / "android_world" / "android_world" / "task_metadata.json",
        limit=12,
    )
    assert len(cases) == 12
    assert all(c.trial_type == "benign" and c.suite == "AndroidWorld" for c in cases)
