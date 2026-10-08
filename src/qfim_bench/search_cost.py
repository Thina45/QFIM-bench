"""
search_cost.py: what Grover search costs when M is unknown, and when every marked item is wanted.

All functions use the closed-form success probability sin^2((2r+1) theta), theta = asin(sqrt(M/N)),
so they describe the ideal algorithm; they say nothing about noise.

  wrong_m_curve         success probability when r is chosen assuming a different M than the true one
  bbht_queries          one run of the Boyer-Brassard-Hoyer-Tapp search, which needs no knowledge of M;
                        returns the number of oracle calls used until a marked item is found
  bbht_mean_queries     Monte Carlo mean of the above
  enumerate_all_queries oracle calls to find all M marked items one after another, removing each once
                        found (about pi/4 * sum_k sqrt(N/(M-k)), roughly (pi/2) sqrt(N M))

Quantum counting is the other standard remedy (estimate M first, then use r_opt); it is not implemented.
"""

from __future__ import annotations

from math import ceil, pi, sqrt

import numpy as np

from qfim_bench.circuit import optimal_iterations, theoretical_success_probability


def wrong_m_curve(true_M: int, assumed_M: int, N: int, r_max: int | None = None) -> dict:
    """P(r) for the true M, and the success probability obtained by using r_opt(assumed_M)."""
    r_used = optimal_iterations(assumed_M, N)
    r_max = r_max if r_max is not None else max(optimal_iterations(1, N), r_used) + 1
    return {
        "true_M": true_M,
        "assumed_M": assumed_M,
        "r_used": r_used,
        "p_with_r_used": theoretical_success_probability(true_M, N, r_used),
        "p_at_true_r_opt": theoretical_success_probability(true_M, N, optimal_iterations(true_M, N)),
        "curve": [theoretical_success_probability(true_M, N, r) for r in range(r_max + 1)],
    }


def bbht_queries(true_M: int, N: int, rng: np.random.Generator, lam: float = 6 / 5) -> int:
    """
    One BBHT run. Each round draws j uniformly from [0, m), applies j Grover iterations (j oracle
    calls), measures, and spends one more oracle call checking the outcome; m grows by lam up to
    sqrt(N). Stops at the first marked outcome. If every item is marked the first measurement ends it.
    """
    if not 0 < true_M <= N:
        raise ValueError("true_M must satisfy 0 < M <= N")
    m, queries = 1.0, 0
    cap = sqrt(N)
    while True:
        j = int(rng.integers(0, max(1, ceil(m))))
        queries += j + 1
        if rng.random() < theoretical_success_probability(true_M, N, j):
            return queries
        m = min(lam * m, cap)


def bbht_mean_queries(true_M: int, N: int, runs: int = 2000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    return float(np.mean([bbht_queries(true_M, N, rng) for _ in range(runs)]))


def enumerate_all_queries(N: int, M: int) -> float:
    """Estimated oracle calls to find all M marked items when each is removed after being found."""
    return float(sum(pi / 4 * sqrt(N / (M - k)) for k in range(M)))
