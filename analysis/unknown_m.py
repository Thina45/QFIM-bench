"""Phase 2G: what happens when r is chosen assuming the wrong M.

N = 32. For each true M and assumed M, the success probability when r = r_opt(assumed M), computed
from the closed form and checked against the exact noiseless circuit statevector. Also: the mean
oracle calls of the BBHT search (no knowledge of M) against its published bound, and the cost of
enumerating all M marked items one by one (about (pi/2) sqrt(N M) calls).

    python analysis/unknown_m.py
"""

import json
from math import sqrt
from pathlib import Path

from qfim_bench.circuit import exact_success_probability, optimal_iterations
from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.search_cost import bbht_mean_queries, enumerate_all_queries, wrong_m_curve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
N, NQ = 32, 5


def marked_set(M):
    return [i for i in range(N) if bin(i).count("1") == 2][:M]


def main() -> None:
    rows = []
    for true_M in (1, 2, 4):
        for assumed in (1, 2, 3, 4, 6, 8):
            c = wrong_m_curve(true_M, assumed, N)
            exact = exact_success_probability(NQ, 0, c["r_used"], initial_state="uniform",
                                              marked_states=marked_set(true_M))
            assert abs(exact - c["p_with_r_used"]) < 1e-9
            rows.append({"true_M": true_M, "assumed_M": assumed, "r_used": c["r_used"],
                         "p_with_r_used": c["p_with_r_used"], "p_best_possible": c["p_at_true_r_opt"],
                         "exact_circuit_p": exact})
            print(f"true M={true_M} assumed M={assumed}: r={c['r_used']}  P={c['p_with_r_used']:.4f} "
                  f"(best {c['p_at_true_r_opt']:.4f})")
    bbht = []
    for M in (1, 2, 4, 8, 16):
        mean = bbht_mean_queries(M, N, runs=5000, seed=M)
        bbht.append({"M": M, "bbht_mean_oracle_calls": mean, "bound_9_over_2_sqrt_N_over_M": 4.5 * sqrt(N / M),
                     "known_M_r_opt_plus_1": optimal_iterations(M, N) + 1,
                     "enumerate_all_M_calls": enumerate_all_queries(N, M)})
        print(bbht[-1])
    (OUT / "unknown_m.json").write_text(json.dumps({"N": N, "wrong_m": rows, "bbht_and_enumeration": bbht}, indent=2),
                                        encoding="utf-8")
    write_experiment_manifest(str(OUT / "unknown_m_manifest.json"), {"script": "analysis/unknown_m.py"}, overwrite=True)


if __name__ == "__main__":
    main()
