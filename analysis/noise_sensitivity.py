"""Phase 2B: noise-model sensitivity sweep.

Does the noise model discriminate weak from strong noise at the sparse operating point, rather than
just agreeing near M/N? Two parts, both FakeMarrakesh at optimization level 3, uniform start,
matched diffusion, 8192 shots, 3 seeded repeats (shot noise only; the transpile is fixed):

  uniform scaling   all four error sources multiplied by 0, 0.25, 0.5, 1, 2 together
  one source off    each source (1Q gates, 2Q gates, readout, relaxation) set to 0 with the other
                    three left at 1, to show which source drives the loss of amplification

Points: (n=5, M=2) and (n=3, M=1), r = 0..r_opt+2. Marked set: first M weight-2 basis states.
At scale 0 the curve must return to the analytical one; that is checked and recorded.

    python analysis/noise_sensitivity.py --seed 42
"""

import argparse
import json
import math
from pathlib import Path

from qfim_bench.backends import NoisySimulatorBackend
from qfim_bench.circuit import build_grover_circuit, optimal_iterations, theoretical_success_probability
from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.noise_scaling import NoiseScales

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
POINTS = [(5, 2), (3, 1)]
CONFIGS = (
    [(f"all x{s:g}", NoiseScales.uniform(s)) for s in (0, 0.25, 0.5, 1, 2)]
    + [("1Q off", NoiseScales(0, 1, 1, 1)), ("2Q off", NoiseScales(1, 0, 1, 1)),
       ("readout off", NoiseScales(1, 1, 0, 1)), ("relaxation off", NoiseScales(1, 1, 1, 0))]
)


def marked_set(n, M):
    return [i for i in range(2**n) if bin(i).count("1") == 2][:M]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    seeds = [args.seed + 100 + k for k in range(args.repeats)]
    result = {"seed": args.seed, "shots": args.shots, "repeat_seeds": seeds, "cells": []}

    for label, scales in CONFIGS:
        noisy = NoisySimulatorBackend(seed=args.seed, optimization_level=3, noise_scales=scales)
        for n, M in POINTS:
            marked = marked_set(n, M)
            keys = {format(i, f"0{n}b") for i in marked}
            for r in range(0, optimal_iterations(M, 2**n) + 3):
                qc, _ = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked)
                reps = noisy.run_repeats(qc, args.shots, seeds)
                ps = [sum(c for k, c in x.counts.items() if k in keys) / args.shots for x in reps]
                mean = sum(ps) / len(ps)
                sd = math.sqrt(sum((x - mean) ** 2 for x in ps) / (len(ps) - 1))
                cell = {"config": label, "scales": scales.__dict__, "n": n, "M": M, "r": r,
                        "analytical": theoretical_success_probability(M, 2**n, r),
                        "noisy_repeats": ps, "noisy_mean": mean, "noisy_sd": sd}
                result["cells"].append(cell)
                print(f"{label:15s} n={n} M={M} r={r}: analytical {cell['analytical']:.3f} noisy {mean:.3f} +/- {sd:.3f}",
                      flush=True)
        (OUT / "noise_sensitivity.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    write_experiment_manifest(str(OUT / "noise_sensitivity_manifest.json"),
                              {"seed": args.seed, "shots": args.shots, "repeats": args.repeats,
                               "script": "analysis/noise_sensitivity.py"}, overwrite=True)


if __name__ == "__main__":
    main()
