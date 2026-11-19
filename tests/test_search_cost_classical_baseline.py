"""Classical query baseline P_c(q): optimal success probability from q queries without replacement."""

from math import comb

import pytest

from qfim_bench.search_cost import classical_query_success_probability


def test_zero_queries_gives_prior_rate():
    # No information drawn yet: success probability is the marked fraction M/N, matching the
    # hardware r=0 baseline (measuring the initial uniform superposition).
    assert classical_query_success_probability(M=4, N=32, q=0) == pytest.approx(4 / 32)


def test_all_queries_always_succeed():
    assert classical_query_success_probability(M=4, N=32, q=32) == 1.0
    assert classical_query_success_probability(M=4, N=32, q=40) == 1.0


def test_matches_hand_computed_value():
    # M=1, N=8, q=2: P = 1 - C(7,2)/C(8,2) * (1 - 1/6) = 1 - (21/28)*(5/6) = 1 - 0.625 = 0.375
    p = classical_query_success_probability(M=1, N=8, q=2)
    assert p == pytest.approx(1 - (comb(7, 2) / comb(8, 2)) * (1 - 1 / 6))
    assert p == pytest.approx(0.375)


def test_monotonic_in_q():
    probs = [classical_query_success_probability(M=2, N=16, q=q) for q in range(0, 15)]
    assert all(b >= a for a, b in zip(probs, probs[1:]))


def test_boundary_q_equals_n_minus_m():
    # N=8, M=1 -> N-M=7: P = 1 - C(7,7)/C(8,7) = 1 - 1/8
    assert classical_query_success_probability(M=1, N=8, q=7) == pytest.approx(1 - 1 / 8)


def test_rejects_invalid_m():
    with pytest.raises(ValueError):
        classical_query_success_probability(M=0, N=8, q=1)
    with pytest.raises(ValueError):
        classical_query_success_probability(M=9, N=8, q=1)


def test_rejects_negative_q():
    with pytest.raises(ValueError):
        classical_query_success_probability(M=1, N=8, q=-1)
