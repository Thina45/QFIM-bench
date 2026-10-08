"""
tvd_calibration.py: total variation distance with a calibrated noise floor.

The empirical TVD between a finite-shot histogram and a distribution is biased upward even when
the two agree exactly. For 32 outcomes and 8192 shots the floor is about 0.0245 against a known
distribution and about 0.0345 between two independent runs. A TVD has to be read against that
floor, so this module provides:

  * tvd_null_distribution   Monte Carlo TVD when the data truly follow a given distribution
  * null_floor              its mean (the bias)
  * tvd_pvalue              p-value for "these counts came from that distribution"
  * two_sample_tvd_pvalue   permutation p-value for "these two runs share a distribution"
  * chi_square_test / g_test   goodness-of-fit with small-expected-count bins pooled
  * tvd_ci_coverage         empirical coverage of a repeat-based confidence interval for the TVD

Distributions are numpy arrays over the same ordered outcomes (use counts_vector to build them).
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def counts_vector(counts: dict[str, int], n_bits: int) -> np.ndarray:
    """Counts dict -> integer vector of length 2**n_bits ordered by int(key, 2)."""
    v = np.zeros(2**n_bits, dtype=np.int64)
    for key, c in counts.items():
        v[int(key.replace(" ", ""), 2)] += c
    return v


def tvd(p: np.ndarray, q: np.ndarray) -> float:
    return 0.5 * float(np.abs(np.asarray(p, float) - np.asarray(q, float)).sum())


def tvd_null_distribution(p: np.ndarray, shots: int, draws: int = 2000, seed: int = 0) -> np.ndarray:
    """TVD(empirical, p) over `draws` simulated histograms of `shots` shots from p."""
    rng = np.random.default_rng(seed)
    p = np.asarray(p, float) / np.sum(p)
    samples = rng.multinomial(shots, p, size=draws) / shots
    return 0.5 * np.abs(samples - p).sum(axis=1)


def null_floor(p: np.ndarray, shots: int, draws: int = 2000, seed: int = 0) -> float:
    """Expected TVD between a `shots`-shot histogram and its own generating distribution."""
    return float(tvd_null_distribution(p, shots, draws, seed).mean())


def tvd_pvalue(counts: np.ndarray, p: np.ndarray, draws: int = 5000, seed: int = 0) -> dict:
    """
    One-sided Monte Carlo p-value: how often a histogram truly drawn from p is at least as far
    from p as the observed one. Also returns the null floor and the bias-corrected TVD.
    """
    counts = np.asarray(counts)
    shots = int(counts.sum())
    p = np.asarray(p, float) / np.sum(p)
    observed = tvd(counts / shots, p)
    null = tvd_null_distribution(p, shots, draws, seed)
    return {
        "tvd": observed,
        "null_floor": float(null.mean()),
        "bias_corrected_tvd": observed - float(null.mean()),
        "p_value": float((1 + np.sum(null >= observed)) / (1 + draws)),
    }


def two_sample_tvd_pvalue(counts_a: np.ndarray, counts_b: np.ndarray, draws: int = 2000, seed: int = 0) -> dict:
    """Permutation test: shuffle which run each shot belongs to; compare the TVD between runs."""
    counts_a, counts_b = np.asarray(counts_a), np.asarray(counts_b)
    na, nb = int(counts_a.sum()), int(counts_b.sum())
    observed = tvd(counts_a / na, counts_b / nb)
    pooled = np.repeat(np.arange(len(counts_a)), counts_a + counts_b)
    rng = np.random.default_rng(seed)
    k = len(counts_a)
    null = np.empty(draws)
    for i in range(draws):
        rng.shuffle(pooled)
        a = np.bincount(pooled[:na], minlength=k) / na
        b = np.bincount(pooled[na:], minlength=k) / nb
        null[i] = tvd(a, b)
    return {
        "tvd": observed,
        "null_floor": float(null.mean()),
        "p_value": float((1 + np.sum(null >= observed)) / (1 + draws)),
    }


def _pooled(observed: np.ndarray, expected: np.ndarray, min_expected: float):
    """Merge outcomes whose expected count is below min_expected into one pooled bin."""
    small = expected < min_expected
    if not small.any():
        return observed, expected
    obs = np.append(observed[~small], observed[small].sum())
    exp = np.append(expected[~small], expected[small].sum())
    keep = exp > 0
    return obs[keep], exp[keep]


def chi_square_test(counts: np.ndarray, p: np.ndarray, min_expected: float = 5.0) -> dict:
    """Pearson chi-square goodness of fit of counts to p (pooling bins with expected < min_expected)."""
    counts = np.asarray(counts, float)
    expected = np.asarray(p, float) / np.sum(p) * counts.sum()
    obs, exp = _pooled(counts, expected, min_expected)
    stat = float(((obs - exp) ** 2 / exp).sum())
    dof = len(obs) - 1
    return {"statistic": stat, "dof": dof, "p_value": float(stats.chi2.sf(stat, dof)), "bins": len(obs)}


def g_test(counts: np.ndarray, p: np.ndarray, min_expected: float = 5.0) -> dict:
    """Likelihood-ratio (G) goodness-of-fit test of counts to p."""
    counts = np.asarray(counts, float)
    expected = np.asarray(p, float) / np.sum(p) * counts.sum()
    obs, exp = _pooled(counts, expected, min_expected)
    mask = obs > 0
    stat = float(2 * (obs[mask] * np.log(obs[mask] / exp[mask])).sum())
    dof = len(obs) - 1
    return {"statistic": stat, "dof": dof, "p_value": float(stats.chi2.sf(stat, dof)), "bins": len(obs)}


def tvd_ci_coverage(
    p_true: np.ndarray,
    q: np.ndarray,
    shots: int = 8192,
    repeats: int = 5,
    sims: int = 400,
    confidence: float = 0.95,
    seed: int = 0,
) -> dict:
    """
    How often the repeat-based t-interval for TVD(empirical, q) (the interval qfim-bench's
    tvd_with_uncertainty reports) contains the TRUE distance TVD(p_true, q).

    Because the empirical TVD carries the upward bias described in the module docstring, this
    coverage falls well below the nominal level when p_true is close to q. The same simulation also
    reports how often the null-floor-corrected interval (interval minus the null floor) covers.
    """
    rng = np.random.default_rng(seed)
    p_true = np.asarray(p_true, float) / np.sum(p_true)
    q = np.asarray(q, float) / np.sum(q)
    truth = tvd(p_true, q)
    floor = null_floor(p_true, shots, 2000, seed + 1)
    t = stats.t.ppf(0.5 + confidence / 2, repeats - 1)
    hit_naive = hit_corrected = 0
    for _ in range(sims):
        samples = rng.multinomial(shots, p_true, size=repeats) / shots
        vals = 0.5 * np.abs(samples - q).sum(axis=1)
        half = t * vals.std(ddof=1) / np.sqrt(repeats)
        lo, hi = vals.mean() - half, vals.mean() + half
        hit_naive += lo <= truth <= hi
        hit_corrected += (lo - floor) <= truth <= (hi - floor)
    return {"true_tvd": truth, "null_floor": floor, "nominal": confidence,
            "coverage_naive": hit_naive / sims, "coverage_floor_corrected": hit_corrected / sims}
