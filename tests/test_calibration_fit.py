"""Intervals, TVD calibration and the fidelity-decay fit, each checked against a known truth."""

import numpy as np
import pytest

from qfim_bench.fit import decay_model, fit_fidelity_decay
from qfim_bench.intervals import clopper_pearson_interval, marked_probability_with_interval, wilson_interval
from qfim_bench.tvd_calibration import (
    chi_square_test,
    counts_vector,
    g_test,
    null_floor,
    tvd,
    tvd_ci_coverage,
    tvd_pvalue,
    two_sample_tvd_pvalue,
)

UNIFORM32 = np.full(32, 1 / 32)


# ---- intervals --------------------------------------------------------------------------------

def test_wilson_half_width_at_p08_matches_normal_approximation():
    lo, hi = wilson_interval(6554, 8192)  # p = 0.8
    assert (hi - lo) / 2 == pytest.approx(1.96 * np.sqrt(0.8 * 0.2 / 8192), abs=1e-4)  # about 0.0087


def test_wilson_and_clopper_pearson_edge_cases():
    assert wilson_interval(0, 100)[0] == 0.0
    assert clopper_pearson_interval(0, 100)[0] == 0.0
    assert clopper_pearson_interval(100, 100)[1] == 1.0
    assert clopper_pearson_interval(0, 100)[1] == pytest.approx(1 - 0.025 ** (1 / 100), rel=1e-9)  # exact: 0.0362
    lo_w, hi_w = wilson_interval(50, 100)
    lo_c, hi_c = clopper_pearson_interval(50, 100)
    assert lo_c <= lo_w and hi_c >= hi_w  # exact interval is the wider one


@pytest.mark.parametrize("fn", [wilson_interval, clopper_pearson_interval])
def test_interval_coverage_is_near_nominal(fn):
    rng = np.random.default_rng(1)
    p, n, sims = 0.3, 500, 2000
    hits = 0
    for k in rng.binomial(n, p, size=sims):
        lo, hi = fn(int(k), n)
        hits += lo <= p <= hi
    assert 0.93 <= hits / sims <= 0.98  # nominal 0.95; SD of the estimate is 0.005


def test_marked_probability_with_interval():
    est, lo, hi = marked_probability_with_interval({"001": 30, "010": 70}, {"001"})
    assert est == 0.3 and lo < 0.3 < hi


def test_interval_input_validation():
    with pytest.raises(ValueError):
        wilson_interval(5, 0)
    with pytest.raises(ValueError):
        wilson_interval(11, 10)


# ---- TVD calibration -----------------------------------------------------------------------------

def test_null_floor_matches_the_value_quoted_in_the_audit():
    # 32 outcomes, 8192 shots, uniform truth: about 0.0245 (the audit's multinomial-simulation value)
    assert null_floor(UNIFORM32, 8192, draws=3000, seed=3) == pytest.approx(0.0245, abs=0.002)


def test_two_run_floor_is_larger_by_about_sqrt_two():
    a = np.random.default_rng(5).multinomial(8192, UNIFORM32)
    b = np.random.default_rng(6).multinomial(8192, UNIFORM32)
    res = two_sample_tvd_pvalue(a, b, draws=800, seed=2)
    assert res["null_floor"] == pytest.approx(0.0345, abs=0.003)
    assert res["p_value"] > 0.05  # same distribution: the test must not reject


def test_pvalue_does_not_reject_the_truth_and_rejects_a_shifted_distribution():
    rng = np.random.default_rng(11)
    same = rng.multinomial(8192, UNIFORM32)
    assert tvd_pvalue(same, UNIFORM32, draws=1000, seed=1)["p_value"] > 0.05
    shifted = UNIFORM32.copy()
    shifted[0] += 0.05
    shifted /= shifted.sum()
    data = rng.multinomial(8192, shifted)
    res = tvd_pvalue(data, UNIFORM32, draws=1000, seed=1)
    assert res["p_value"] < 0.01
    assert res["bias_corrected_tvd"] < res["tvd"]


def test_pvalues_are_uniform_under_the_null():
    rng = np.random.default_rng(21)
    ps = [tvd_pvalue(rng.multinomial(8192, UNIFORM32), UNIFORM32, draws=300, seed=i)["p_value"] for i in range(150)]
    rejection_rate = float(np.mean(np.array(ps) < 0.05))
    assert rejection_rate <= 0.12  # nominal 0.05; allows for 150-sim sampling noise (SD 0.018)


@pytest.mark.parametrize("test", [chi_square_test, g_test])
def test_goodness_of_fit_tests_behave(test):
    rng = np.random.default_rng(31)
    assert test(rng.multinomial(8192, UNIFORM32), UNIFORM32)["p_value"] > 0.01
    skew = UNIFORM32.copy()
    skew[:4] *= 3
    skew /= skew.sum()
    assert test(rng.multinomial(8192, skew), UNIFORM32)["p_value"] < 1e-6


def test_small_expected_bins_are_pooled():
    p = np.array([0.9, 0.09, 0.005, 0.005])  # expected counts 900, 90, 5, 5 out of 1000
    counts = np.array([900, 90, 5, 5])
    assert chi_square_test(counts, p, min_expected=5.0)["bins"] == 4    # nothing below the cutoff
    assert chi_square_test(counts, p, min_expected=6.0)["bins"] == 3    # the two 5s pool into one
    assert chi_square_test(counts, p, min_expected=100.0)["bins"] == 2  # 90 + 5 + 5 pool into one


def test_counts_vector_orders_by_integer_value():
    v = counts_vector({"01": 3, "10": 5}, 2)
    assert list(v) == [0, 3, 5, 0]


def test_naive_tvd_interval_is_not_calibrated_near_zero_and_the_correction_fixes_it():
    cov = tvd_ci_coverage(UNIFORM32, UNIFORM32, sims=300, seed=4)
    assert cov["true_tvd"] == 0.0
    assert cov["coverage_naive"] < 0.1  # interval sits at the 0.0245 floor, truth is 0
    assert cov["coverage_floor_corrected"] > 0.8


# ---- fidelity-decay fit ---------------------------------------------------------------------------

def _synthetic(f, pn, seed, shots=8192, M=1, N=32, steps=range(0, 7)):
    theta = np.arcsin(np.sqrt(M / N))
    g = np.array(list(steps), float)
    p_ideal = np.sin((2 * g + 1) * theta) ** 2
    p = decay_model(g, p_ideal, f, pn)
    k = np.random.default_rng(seed).binomial(shots, p)
    return g, p_ideal, k, np.full(len(g), shots)


def test_fit_recovers_known_parameters():
    g, p_ideal, k, n = _synthetic(0.85, 1 / 32, seed=1)
    fit = fit_fidelity_decay(g, p_ideal, k, n, n_bootstrap=100, seed=1)
    assert fit.f == pytest.approx(0.85, abs=0.02)
    assert fit.p_noise == pytest.approx(1 / 32, abs=0.02)
    assert fit.f_ci[0] <= 0.85 <= fit.f_ci[1]
    assert fit.half_life_steps == pytest.approx(np.log(0.5) / np.log(fit.f))


def test_fit_with_no_decay_returns_f_near_one():
    g, p_ideal, k, n = _synthetic(1.0, 0.2, seed=2)
    fit = fit_fidelity_decay(g, p_ideal, k, n, n_bootstrap=60, seed=2)
    assert fit.f > 0.97


def test_fit_confidence_interval_coverage():
    """Truth f = 0.8; the 95% interval should cover it in most of 40 simulated datasets."""
    hits = 0
    sims = 40
    for s in range(sims):
        g, p_ideal, k, n = _synthetic(0.8, 0.1, seed=100 + s, shots=2000)
        fit = fit_fidelity_decay(g, p_ideal, k, n, n_bootstrap=80, seed=s)
        hits += fit.f_ci[0] <= 0.8 <= fit.f_ci[1]
    assert hits / sims >= 0.85  # nominal 0.95; SD of the estimate with 40 sims is 0.035


def test_fit_rejects_bad_input():
    with pytest.raises(ValueError):
        fit_fidelity_decay([0, 1], [0.1, 0.2], [1, 2], [10, 10])  # fewer than 3 points
    with pytest.raises(ValueError):
        fit_fidelity_decay([0, 1, 2], [0.1, 0.2], [1, 2, 3], [10, 10, 10])  # length mismatch
    assert tvd(np.array([1.0, 0]), np.array([0, 1.0])) == 1.0
