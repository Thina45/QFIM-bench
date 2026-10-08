"""
intervals.py: binomial confidence intervals for a probability measured from shots.

Every probability reported from a counts dictionary (marked-state probability, precision-like
fractions) should carry one of these. At p = 0.8 and 8192 shots the 95% half-width is about 0.0085.

wilson_interval is the default (good coverage, never leaves [0, 1]); clopper_pearson_interval is
the exact, conservative alternative. Both are generic and import nothing from the QFIM code.
"""

from __future__ import annotations

from math import sqrt

from scipy import stats


def _check(k: int, n: int) -> None:
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")


def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    _check(k, n)
    z = stats.norm.ppf(0.5 + confidence / 2)
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, centre - half)  # exact at the boundary, not 3e-18
    hi = 1.0 if k == n else min(1.0, centre + half)
    return lo, hi


def clopper_pearson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Exact (Clopper-Pearson) interval for k successes in n trials."""
    _check(k, n)
    alpha = 1 - confidence
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def marked_probability_with_interval(
    counts: dict[str, int], marked_keys: set[str], confidence: float = 0.95, method: str = "wilson"
) -> tuple[float, float, float]:
    """(estimate, low, high) of the probability mass on marked_keys in a counts dictionary."""
    n = sum(counts.values())
    k = sum(c for key, c in counts.items() if key in marked_keys)
    interval = {"wilson": wilson_interval, "clopper-pearson": clopper_pearson_interval}[method]
    lo, hi = interval(k, n, confidence)
    return k / n, lo, hi
