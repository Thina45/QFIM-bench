"""Phase 2 items 1 and 2: fixed-M/N feasibility sweep and oracle-synthesis comparison.

(n, M) in {(2,1), (3,1), (4,2), (5,4)}, uniform start, matched diffusion, three oracle styles
(mcx reference, mcz, mcx_vchain), r = 0..r_opt+2, FakeMarrakesh at optimization level 3 (the
hardware setting), 8192 shots, 5 seeded repeats. The circuit is transpiled once per cell and
sampled with five simulator seeds, so the interval below covers shot noise only (the transpile
is fixed by seed_transpiler); this is stated wherever the numbers are used.

The operating-point rule in review/OPERATING_POINT_CRITERION.md is implemented verbatim in
`passes_criterion`. It is applied here only to produce a pass/fail column; nothing in it was tuned
after these results were seen.

    python analysis/feasibility_sweep.py --seed 42
"""

import argparse
import json
import math
from pathlib import Path

from qfim_bench.backends import NoisySimulatorBackend
from qfim_bench.circuit import (
    ORACLE_STYLES,
    build_grover_circuit,
    exact_success_probability,
    optimal_iterations,
    theoretical_success_probability,
)
from qfim_bench.manifest import write_experiment_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
POINTS = [(2, 1), (3, 1), (4, 2), (5, 4)]
T975_DF4 = 2.7764451051977987  # two-sided 95% t quantile, 4 degrees of freedom (5 repeats)


def marked_set(n: int, M: int) -> list[int]:
    return [i for i in range(2**n) if bin(i).count("1") == 2][:M]


def p_marked(counts: dict, marked: list[int], n: int) -> float:
    keys = {format(i, f"0{n}b") for i in marked}
    return sum(c for k, c in counts.items() if k in keys) / sum(counts.values())


def two_qubit_count(circ) -> int:
    return sum(v for k, v in circ.count_ops().items() if k in ("cz", "ecr", "cx"))


def passes_criterion(cells: list[dict], n: int, M: int) -> dict:
    """review/OPERATING_POINT_CRITERION.md, rules 1-4, evaluated at r_opt for one (n, M, style)."""
    by_r = {c["r"]: c for c in cells}
    r_opt = optimal_iterations(M, 2**n)
    c, c0 = by_r[r_opt], by_r[0]
    P, P0 = c["noisy_mean"], c0["noisy_mean"]
    se = c["noisy_sd"] / math.sqrt(len(c["noisy_repeats"]))
    p_max = max(x["noisy_mean"] for x in cells)
    sd_max = c["noisy_sd"]
    rules = {
        "1_ratio_ge_3": P >= 3 * P0,
        "2_floor_ge_0.40": P >= 0.40,
        "3_gap_over_M/N_ge_0.20": (P - M / 2**n) >= 0.20 and se < 0.01,
        "4_is_max_within_sd": P >= p_max - sd_max,
    }
    return {"r_opt": r_opt, "P_at_r_opt": P, "P_at_0": P0, "rules": rules, "pass": all(rules.values()),
            "two_qubit_gates_at_r_opt": c["transpiled_two_qubit_gates"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    noisy = NoisySimulatorBackend(seed=args.seed, optimization_level=3)
    repeat_seeds = [args.seed + 100 + k for k in range(args.repeats)]
    result = {"seed": args.seed, "shots": args.shots, "repeat_seeds": repeat_seeds,
              "optimization_level": 3, "points": [], "criterion": []}

    for n, M in POINTS:
        marked = marked_set(n, M)
        r_opt = optimal_iterations(M, 2**n)
        for style in ORACLE_STYLES:
            cells = []
            for r in range(0, r_opt + 3):
                qc, _ = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked, oracle_style=style)
                tq = noisy.transpile(qc)
                reps = noisy.sample(tq, args.shots, repeat_seeds)
                ps = [p_marked(x.counts, marked, n) for x in reps]
                mean = sum(ps) / len(ps)
                sd = math.sqrt(sum((x - mean) ** 2 for x in ps) / (len(ps) - 1))
                half = T975_DF4 * sd / math.sqrt(len(ps))
                cell = {
                    "n": n, "M": M, "style": style, "r": r, "marked": marked, "r_opt": r_opt,
                    "analytical": theoretical_success_probability(M, 2**n, r),
                    "noiseless_exact": exact_success_probability(n, 0, r, initial_state="uniform",
                                                                 marked_states=marked, oracle_style=style),
                    "noisy_repeats": ps, "noisy_mean": mean, "noisy_sd": sd,
                    "ci95_low": mean - half, "ci95_high": mean + half,
                    "transpiled_depth": tq.depth(), "transpiled_two_qubit_gates": two_qubit_count(tq),
                    "logical_qubits": qc.num_qubits,
                    "noisy_counts": [x.counts for x in reps],
                }
                cells.append(cell)
                print(f"n={n} M={M} {style:10s} r={r}: analytical {cell['analytical']:.3f} "
                      f"noisy {mean:.3f} [{cell['ci95_low']:.3f},{cell['ci95_high']:.3f}] "
                      f"depth {cell['transpiled_depth']} 2Q {cell['transpiled_two_qubit_gates']}", flush=True)
            result["points"].extend(cells)
            crit = passes_criterion(cells, n, M)
            crit.update({"n": n, "M": M, "style": style})
            result["criterion"].append(crit)
            print(f"   criterion n={n} M={M} {style}: pass={crit['pass']} {crit['rules']}", flush=True)
            (OUT / "feasibility_sweep.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    write_experiment_manifest(str(OUT / "feasibility_sweep_manifest.json"),
                              {"seed": args.seed, "shots": args.shots, "repeats": args.repeats,
                               "script": "analysis/feasibility_sweep.py"}, overwrite=True)


if __name__ == "__main__":
    main()
