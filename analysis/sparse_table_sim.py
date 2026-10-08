"""Simulator numbers for the sparse-marking table (STOP-GATE 2): noiseless and 5x FakeMarrakesh.

N = 32 (5 qubits), M in {1, 2, 3, 4}, uniform start, matched diffusion, 8192 shots, r over the
columns of the reference table (M=1: 0..5, M=2: 0..4, M=3: 0..3, M=4: 0..3).

Marked-set rule (fixed in advance, not tuned): the first M basis states of Hamming weight 2 in
increasing index order, i.e. {3}, {3,5}, {3,5,6}, {3,5,6,9}. Weight-2 states avoid |00000>, the
state that relaxation (T1) drifts toward, which would otherwise bias the noisy results. The ideal
curves do not depend on which states are marked.

For each (M, r): the analytical value, the exact noiseless statevector value, one seeded noiseless
sample, and five noisy repeats (the circuit is transpiled once at optimisation level 3, matching the
hardware configuration, and sampled with five different simulator seeds). Raw counts are saved.

    python analysis/sparse_table_sim.py --seed 42
"""

import argparse
import json
import math
from pathlib import Path

from qiskit_aer import AerSimulator

from qfim_bench.backends import NoisySimulatorBackend
from qfim_bench.circuit import (
    build_grover_circuit,
    exact_success_probability,
    optimal_iterations,
    theoretical_success_probability,
)
from qfim_bench.manifest import write_experiment_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
N_QUBITS = 5
R_MAX = {1: 5, 2: 4, 3: 3, 4: 3}


def marked_set(M: int) -> list[int]:
    weight2 = [i for i in range(2**N_QUBITS) if bin(i).count("1") == 2]
    return weight2[:M]


def p_marked(counts: dict, marked: list[int]) -> float:
    keys = {format(i, f"0{N_QUBITS}b") for i in marked}
    return sum(c for k, c in counts.items() if k in keys) / sum(counts.values())


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
              "marked_set_rule": "first M basis states of Hamming weight 2, increasing index", "cells": []}

    for M in (1, 2, 3, 4):
        marked = marked_set(M)
        for r in range(0, R_MAX[M] + 1):
            qc, info = build_grover_circuit(N_QUBITS, 0, r, initial_state="uniform", marked_states=marked)
            noiseless = AerSimulator(seed_simulator=args.seed).run(qc, shots=args.shots).result().get_counts()
            reps = noisy.run_repeats(qc, args.shots, repeat_seeds)
            noisy_p = [p_marked(x.counts, marked) for x in reps]
            mean = sum(noisy_p) / len(noisy_p)
            sd = math.sqrt(sum((x - mean) ** 2 for x in noisy_p) / (len(noisy_p) - 1))
            cell = {
                "M": M, "r": r, "marked": marked, "r_opt": optimal_iterations(M, 2**N_QUBITS),
                "analytical": theoretical_success_probability(M, 2**N_QUBITS, r),
                "noiseless_exact": exact_success_probability(N_QUBITS, 0, r, initial_state="uniform", marked_states=marked),
                "noiseless_sampled": p_marked(noiseless, marked),
                "noisy_repeats": noisy_p, "noisy_mean": mean, "noisy_sd": sd,
                "noiseless_counts": noiseless, "noisy_counts": [x.counts for x in reps],
            }
            result["cells"].append(cell)
            print(f"M={M} r={r}: analytical {cell['analytical']:.4f}  noiseless {cell['noiseless_sampled']:.4f}  "
                  f"noisy {mean:.4f} +/- {sd:.4f}", flush=True)
            (OUT / "sparse_table_sim.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    write_experiment_manifest(str(OUT / "sparse_table_sim_manifest.json"),
                              {"seed": args.seed, "shots": args.shots, "repeats": args.repeats,
                               "script": "analysis/sparse_table_sim.py"}, overwrite=True)


if __name__ == "__main__":
    main()
