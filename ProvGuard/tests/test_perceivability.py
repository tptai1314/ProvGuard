from provguard.perceivability import (
    PerceivabilityEvidence,
    PerceivabilityThresholds,
    combined_opacity,
    contrast_ratio,
    is_perceivable,
)


def test_equations_and_conservative_missing_evidence() -> None:
    assert combined_opacity([0.5, 0.5]) == 0.75
    assert contrast_ratio(1, 0) == 21
    thresholds = PerceivabilityThresholds()
    good = PerceivabilityEvidence(1, 1, 1, 0, 1, 100)
    missing = PerceivabilityEvidence(None, 1, 1, 0, 1, 100)
    assert is_perceivable(good, thresholds)
    assert not is_perceivable(missing, thresholds)

