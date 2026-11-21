from provguard.schemas import EquivalenceMode
from provguard.synthetic import SYNTHETIC_NOTICE, build_scenarios, run_synthetic_trials


def test_synthetic_channels_and_honest_labels() -> None:
    channels = {scenario.channel for scenario in build_scenarios()}
    assert {"webview", "notifications", "foreground_rebinding", "in_app_third_party_g1"} <= channels


def test_output_is_explicitly_synthetic() -> None:
    rows = run_synthetic_trials(
        seed=3,
        repetitions=1,
        trials=1,
        threshold=0.5,
        equivalence=EquivalenceMode.CONTROL,
    )
    assert rows
    assert all(row["result_kind"] == SYNTHETIC_NOTICE for row in rows)

