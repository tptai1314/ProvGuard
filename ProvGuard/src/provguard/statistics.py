"""Analytical gate bounds and confidence intervals from Sections 7.4 and 8.5."""

from __future__ import annotations

import math
from dataclasses import dataclass


def binomial_pass_probability(k: int, q: float, theta: float) -> float:
    """Paper Eq. (6): P[Bin(k,q) >= ceil(theta*k)]."""

    if k < 1 or not 0 <= q <= 1 or not 0 < theta <= 1:
        raise ValueError("Require k>=1, q in [0,1], theta in (0,1]")
    cutoff = math.ceil(theta * k)
    return sum(
        math.comb(k, successes)
        * q**successes
        * (1.0 - q) ** (k - successes)
        for successes in range(cutoff, k + 1)
    )


def bernoulli_kl(x: float, y: float) -> float:
    if not 0 <= x <= 1 or not 0 < y < 1:
        raise ValueError("Require x in [0,1] and y in (0,1)")
    first = 0.0 if x == 0 else x * math.log(x / y)
    second = 0.0 if x == 1 else (1 - x) * math.log((1 - x) / (1 - y))
    return first + second


def false_pass_bounds(k: int, q0: float, theta: float) -> tuple[float, float]:
    """Theorem 2(i): Chernoff-KL and Hoeffding bounds."""

    if not 0 <= q0 < theta <= 1:
        raise ValueError("Require 0 <= q0 < theta <= 1")
    kl_bound = 0.0 if q0 == 0 else math.exp(-k * bernoulli_kl(theta, q0))
    hoeffding = math.exp(-2 * k * (theta - q0) ** 2)
    return kl_bound, hoeffding


def false_escalation_bound(k: int, q1: float, theta: float) -> float:
    """Theorem 2(ii)."""

    if not 0 < theta < q1 <= 1:
        raise ValueError("Require 0 < theta < q1 <= 1")
    return math.exp(-2 * k * (q1 - theta) ** 2)


def hoeffding_trials(q0: float, q1: float, theta: float, delta: float) -> int:
    """Corollary 2: sufficient number of trials for both errors <= delta."""

    if not 0 <= q0 < theta < q1 <= 1 or not 0 < delta < 1:
        raise ValueError("Require q0 < theta < q1 and delta in (0,1)")
    value = max(
        math.log(1 / delta) / (2 * (theta - q0) ** 2),
        math.log(1 / delta) / (2 * (q1 - theta) ** 2),
    )
    return math.ceil(value)


def exact_minimum_trials(
    q0: float,
    q1: float,
    theta: float,
    delta: float,
    maximum: int = 100_000,
) -> int:
    """Smallest k meeting both exact binomial error targets (paper Table 5)."""

    for k in range(1, maximum + 1):
        false_pass = binomial_pass_probability(k, q0, theta)
        false_escalate = 1 - binomial_pass_probability(k, q1, theta)
        if false_pass <= delta and false_escalate <= delta:
            return k
    raise RuntimeError(f"No k <= {maximum} satisfies the requested errors")


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> Interval:
    """95% Wilson score interval used by the evaluation protocol."""

    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("Require total > 0 and successes in [0,total]")
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return Interval(max(0.0, center - half), min(1.0, center + half))


def mcnemar_exact_pvalue(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for discordant paired outcomes."""

    if b < 0 or c < 0:
        raise ValueError("Discordant counts must be non-negative")
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / (2**n)
    return min(1.0, 2 * tail)

