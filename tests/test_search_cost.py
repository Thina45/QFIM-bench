"""Unknown-M handling: wrong-M success probability, BBHT cost, enumeration cost."""

from math import pi, sqrt

import pytest

from qfim_bench.search_cost import bbht_mean_queries, enumerate_all_queries, wrong_m_curve


def test_wrong_m_hurts_exactly_as_the_formula_says():
    c = wrong_m_curve(true_M=4, assumed_M=1, N=32)
    assert c["r_used"] == 4
    # sin^2(9 * asin(sqrt(4/32))), computed independently
    from math import asin, sin
    assert c["p_with_r_used"] == pytest.approx(sin(9 * asin(sqrt(4 / 32))) ** 2, abs=1e-12)
    assert c["p_with_r_used"] < 0.02  # overshooting by two full oscillations lands near a zero
    assert c["p_at_true_r_opt"] == pytest.approx(0.9453, abs=1e-4)


def test_right_m_gives_the_optimum():
    c = wrong_m_curve(true_M=3, assumed_M=3, N=32)
    assert c["p_with_r_used"] == pytest.approx(c["p_at_true_r_opt"])


def test_bbht_stays_within_the_published_bound_and_scales_like_sqrt_n_over_m():
    # Boyer et al.: expected oracle calls <= (9/2) sqrt(N/M)
    for M in (1, 2, 4, 8):
        mean = bbht_mean_queries(M, 64, runs=3000, seed=M)
        assert mean <= 4.5 * sqrt(64 / M)
    assert bbht_mean_queries(1, 64, runs=3000, seed=1) > bbht_mean_queries(8, 64, runs=3000, seed=8)


def test_bbht_is_reproducible():
    assert bbht_mean_queries(2, 32, runs=200, seed=5) == bbht_mean_queries(2, 32, runs=200, seed=5)


def test_enumeration_cost_grows_like_sqrt_nm():
    n = 1024
    ratio = enumerate_all_queries(n, 16) / sqrt(n * 16)
    assert ratio == pytest.approx(pi / 2, rel=0.25)  # (pi/2) sqrt(NM) up to the discrete-sum correction
    assert enumerate_all_queries(n, 16) > enumerate_all_queries(n, 4)
