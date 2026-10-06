"""
statistics.py — shared statistical core for qfim-bench.

Used by noise_analysis.py (TVD with uncertainty) and reproducibility.py
(repeated-run CV/CI), so both modules report statistically grounded numbers
(e.g. "TVD = 0.21 +/- 0.03") rather than bare point estimates.

No quantum dependencies — pure Python/stdlib + nothing beyond basic math,
so this module is trivially unit-testable on its own.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


# --------------------------------------------------------------------------
# Run summaries (mean / SD / CV / confidence interval)
# --------------------------------------------------------------------------

@dataclass
class RunSummary:
    n: int
    mean: float
    sd: float
    cv_percent: float          # coefficient of variation, as a percentage
    ci_low: float
    ci_high: float
    confidence_level: float


def _sample_sd(values: list[float], mean: float) -> float:
    """Sample standard deviation (n-1 denominator). Returns 0.0 for n<2."""
    n = len(values)
    if n < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(variance)


# Two-sided t critical values for common confidence levels, keyed by
# degrees of freedom (df = n - 1). Falls back to the normal (z) critical
# value for df beyond this table, which is an acceptable approximation
# for the sample sizes this tool is meant for (and conservative is fine
# here since we're reporting uncertainty, not chasing significance).
_T_TABLE_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    15: 2.131, 20: 2.086, 30: 2.042,
}
_Z_95 = 1.960


def _critical_value(df: int, confidence_level: float) -> float:
    """
    t critical value for the given degrees of freedom at the given
    confidence level. Only 0.95 is tabulated precisely; other levels fall
    back to the normal approximation, which is noted in the docstring of
    summarize_runs rather than silently hidden.
    """
    if df < 1:
        return 0.0
    if confidence_level == 0.95:
        if df in _T_TABLE_95:
            return _T_TABLE_95[df]
        largest_tabulated = max(k for k in _T_TABLE_95 if k <= df) if any(
            k <= df for k in _T_TABLE_95
        ) else None
        if largest_tabulated is not None and df > 30:
            return _Z_95
        if largest_tabulated is not None:
            return _T_TABLE_95[largest_tabulated]
    # Fallback for confidence levels other than 0.95: normal approximation.
    # 90% -> 1.645, 99% -> 2.576; anything else defaults to 95%'s z-value.
    _Z_TABLE = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    return _Z_TABLE.get(confidence_level, _Z_95)


def summarize_runs(values: list[float], confidence_level: float = 0.95) -> RunSummary:
    """
    Summarize a list of repeated-run measurements (e.g. success probability
    from N repeated hardware jobs, or TVD from N bootstrap resamples).

    Returns mean, sample SD, coefficient of variation (%), and a two-sided
    confidence interval for the mean. For n=1, SD/CV are 0.0 and the CI
    collapses to the single value (there is no variability to estimate from
    a single run — this is reported explicitly as a scope limitation, not
    silently masked, matching the practice in the companion paper for its
    own n=2 reproducibility check).
    """
    if not values:
        raise ValueError("values must be a non-empty list")

    n = len(values)
    mean = sum(values) / n
    sd = _sample_sd(values, mean)
    cv_percent = (sd / mean * 100.0) if mean != 0 else float("nan")

    if n < 2:
        return RunSummary(
            n=n, mean=mean, sd=0.0, cv_percent=0.0,
            ci_low=mean, ci_high=mean, confidence_level=confidence_level,
        )

    se = sd / math.sqrt(n)
    t_crit = _critical_value(n - 1, confidence_level)
    margin = t_crit * se

    return RunSummary(
        n=n, mean=mean, sd=sd, cv_percent=cv_percent,
        ci_low=mean - margin, ci_high=mean + margin,
        confidence_level=confidence_level,
    )


# --------------------------------------------------------------------------
# Total variation distance, with bootstrap uncertainty across repeated runs
# --------------------------------------------------------------------------

def total_variation_distance(p: dict[str, float], q: dict[str, float]) -> float:
    """
    TVD(P, Q) = 0.5 * sum_x |P(x) - Q(x)|

    p and q are probability distributions over basis states (bitstring ->
    probability). Keys missing from one dict are treated as probability 0
    in that distribution. Matches Eq. (7) in the companion paper.
    """
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def counts_to_probabilities(counts: dict[str, int]) -> dict[str, float]:
    """Normalize a Qiskit-style counts dict (bitstring -> shot count) to probabilities."""
    total = sum(counts.values())
    if total == 0:
        raise ValueError("counts must have at least one shot")
    return {k: v / total for k, v in counts.items()}


@dataclass
class TVDReport:
    point_estimate: float
    summary: RunSummary | None   # None if only a single pair of distributions was given


def tvd_with_uncertainty(
    counts_list_p: list[dict[str, int]],
    counts_list_q: list[dict[str, int]],
    confidence_level: float = 0.95,
) -> TVDReport:
    """
    Compute TVD between distribution P and distribution Q, with uncertainty
    estimated across repeated runs rather than reported as a single point
    value.

    counts_list_p / counts_list_q: lists of Qiskit-style counts dicts, one
    per repeated execution (e.g. 5 repeated hardware jobs). If both lists
    have length 1, returns a point estimate with summary=None (no
    variability can be estimated from a single run of each).

    If lengths differ, every (p_i, q_j) pair is used (cross product),
    which is appropriate when P and Q come from independently repeated
    executions (e.g. several noisy-simulation runs vs several hardware
    runs) rather than paired runs.
    """
    if not counts_list_p or not counts_list_q:
        raise ValueError("counts_list_p and counts_list_q must be non-empty")

    pairwise_tvds = []
    for cp in counts_list_p:
        pp = counts_to_probabilities(cp)
        for cq in counts_list_q:
            qq = counts_to_probabilities(cq)
            pairwise_tvds.append(total_variation_distance(pp, qq))

    point_estimate = sum(pairwise_tvds) / len(pairwise_tvds)

    if len(pairwise_tvds) < 2:
        return TVDReport(point_estimate=point_estimate, summary=None)

    summary = summarize_runs(pairwise_tvds, confidence_level=confidence_level)
    return TVDReport(point_estimate=point_estimate, summary=summary)


# --------------------------------------------------------------------------
# Bootstrap confidence interval (generic utility, usable beyond TVD)
# --------------------------------------------------------------------------

def bootstrap_ci(
    values: list[float],
    confidence_level: float = 0.95,
    n_resamples: int = 2000,
    seed: int | None = None,
) -> tuple[float, float]:
    """
    Generic percentile bootstrap confidence interval for the mean of
    `values`. Useful when the normal/t-distribution assumption behind
    summarize_runs' CI is not appropriate (e.g. small, skewed samples).

    Returns (ci_low, ci_high).
    """
    if len(values) < 2:
        raise ValueError("bootstrap_ci requires at least 2 values")

    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)

    means.sort()
    alpha = 1.0 - confidence_level
    lo_idx = int((alpha / 2) * n_resamples)
    hi_idx = int((1 - alpha / 2) * n_resamples) - 1
    hi_idx = min(hi_idx, n_resamples - 1)

    return means[lo_idx], means[hi_idx]
