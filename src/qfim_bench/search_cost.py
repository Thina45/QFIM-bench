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

from math import ceil, comb, pi, sqrt

import numpy as np

from qfim_bench.circuit import optimal_iterations, theoretical_success_probability


def classical_query_success_probability(M: int, N: int, q: int) -> float:
    """
    Optimal classical success probability of finding at least one marked item by drawing q
    distinct items uniformly without replacement (q classical oracle queries), out of M marked
    items among N total:

        P_c(q) = 1 - [C(N-M, q) / C(N, q)] * (1 - M / (N - q))

    q counts queries the same way r counts Grover iterations in this project (one comparison
    point per iteration), so P_c(r) is the baseline to compare against the hardware success
    probability at r Grover iterations.

    At q = N - M, drawing all non-marked items is still possible with C(N-M, q)/C(N, q) > 0, but
    M / (N - q) is undefined (division by zero); every draw of q = N - M items that misses all M
    marked ones is impossible once q > N - M (C(N-M, q) is 0), so P_c(q) = 1 for q > N - M. At
    q = N - M exactly, the second factor's limit is handled as 0 (no items left unseen that could
    still be marked), giving P_c(N - M) = 1 - C(N-M, N-M)/C(N, N-M) = 1 - 1/C(N, N-M).
    """
    if not (0 < M <= N):
        raise ValueError("M must satisfy 0 < M <= N")
    if q < 0:
        raise ValueError("q must be non-negative")
    if q == 0:
        return M / N
    if q >= N:
        return 1.0
    miss_all = comb(N - M, q) / comb(N, q) if N - M >= q else 0.0
    if q == N - M:
        return 1.0 - miss_all
    return 1.0 - miss_all * (1.0 - M / (N - q))


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
