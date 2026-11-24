"""End-to-end test: raw dump -> labelled observation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from provguard.contrast import relative_luminance
from provguard.lattice import IntegrityLabel
from provguard.observation import BuildSettings, build_observation, observation_to_dict
from provguard.schemas import BoundingBox, RegionKind, WindowType
from provguard.uidump import parse_ui_xml
from provguard.windowdump import WindowInfo, display_size_from_dump, parse_window_dump

FIXTURE = Path(__file__).parent / "fixtures" / "obs_settings"


def _build():
    windows_text = (FIXTURE / "windows.txt").read_text(encoding="utf-8-sig")
    windows = parse_window_dump(windows_text)
    nodes = parse_ui_xml(FIXTURE / "ui.xml")
    image = np.full((2424, 1080, 3), 255, dtype=np.uint8)
    return build_observation(
        observation_id="fixture",
        step=0,
        nodes=nodes,
        windows=windows,
        display=display_size_from_dump(windows_text) or (1080, 2424),
        settings=BuildSettings(),
        luminance=relative_luminance(image),
    )


def test_diagnostics_and_counts() -> None:
    result = _build()
    diagnostics = result.diagnostics
    assert diagnostics["nodes_total"] == 73
    assert diagnostics["regions"] == 70
    assert diagnostics["skipped_empty"] == 3
    assert diagnostics["fallback_windows"] == 0
    assert diagnostics["target_package"] == "com.android.settings"
    assert diagnostics["target_uid"] == 1000
    assert diagnostics["has_luminance"] is True


def test_all_nodes_are_labelled_app() -> None:
    result = _build()
    labels = {region.label for region in result.observation.regions}
    assert labels == {IntegrityLabel.APP}
    assert result.diagnostics["label_counts"]["app"] == 70


def test_every_region_has_a_binding() -> None:
    result = _build()
    for region in result.observation.regions:
        assert region.binding is not None
        assert region.binding.window_token
        assert region.binding.owner_uid == 1000
        assert region.binding.digest and len(region.binding.digest) == 16
        assert region.geometry.z_order == 8


def test_contrast_and_perceivability() -> None:
    result = _build()
    text_regions = [region for region in result.observation.regions if region.content]
    assert text_regions
    assert all(region.metadata["contrast"] == pytest.approx(1.0) for region in text_regions)
    assert all(region.provenance.perceivable is False for region in text_regions)
    assert any(region.provenance.perceivable for region in result.observation.regions)


def test_serialization_roundtrip_shape() -> None:
    payload = observation_to_dict(_build())
    assert payload["observation_id"] == "fixture"
    assert payload["display"] == {"width": 1080, "height": 2424}
    assert len(payload["regions"]) == 70
    first = payload["regions"][0]
    assert set(first) >= {
        "region_id",
        "bounds",
        "provenance",
        "label",
        "binding",
        "metadata",
    }
    assert first["provenance"]["window_type"] == "application"


def test_synthesizes_untrusted_tile_for_omitted_overlay_window() -> None:
    windows_text = (FIXTURE / "windows.txt").read_text(encoding="utf-8-sig")
    windows = parse_window_dump(windows_text)
    overlay_win = WindowInfo(
        index=1,
        token="tok_evil_overlay",
        name="com.provguard.attackkit.overlay",
        package="com.provguard.attackkit.overlay",
        uid=10399,
        type_name="APPLICATION_OVERLAY",
        window_type=WindowType.OVERLAY,
        frame=BoundingBox(0.0, 260.0, 1080.0, 380.0),
        alpha=1.0,
        visible=True,
        on_screen=True,
        obscured=False,
        has_surface=True,
    )
    windows_with_overlay = [overlay_win, *windows]
    nodes = parse_ui_xml(FIXTURE / "ui.xml")
    image = np.full((2424, 1080, 3), 255, dtype=np.uint8)
    result = build_observation(
        observation_id="fixture_overlay",
        step=0,
        nodes=nodes,
        windows=windows_with_overlay,
        display=display_size_from_dump(windows_text) or (1080, 2424),
        settings=BuildSettings(),
        luminance=relative_luminance(image),
    )
    synth = [r for r in result.observation.regions if r.kind == RegionKind.TILE]
    assert len(synth) == 1
    assert synth[0].label == IntegrityLabel.UNTRUSTED
    assert synth[0].geometry.bounds == BoundingBox(0.0, 260.0, 1080.0, 380.0)
    assert result.diagnostics["label_counts"]["unt"] == 1

