import math

from provguard.statistics import (
    binomial_pass_probability,
    exact_minimum_trials,
    false_pass_bounds,
    hoeffding_trials,
    mcnemar_exact_pvalue,
    wilson_interval,
)


def test_eq6_and_table5_reference_case() -> None:
    assert math.isclose(binomial_pass_probability(1, 0.2, 0.5), 0.2)
    assert exact_minimum_trials(0.2, 0.8, 0.5, 0.01) == 13
    assert hoeffding_trials(0.2, 0.8, 0.5, 0.01) == 26


def test_bounds_and_intervals_are_valid() -> None:
    kl, hoeffding = false_pass_bounds(10, 0.2, 0.5)
    assert 0 <= kl <= hoeffding <= 1
    interval = wilson_interval(5, 10)
    assert interval.lower < 0.5 < interval.upper
    assert mcnemar_exact_pvalue(0, 0) == 1

