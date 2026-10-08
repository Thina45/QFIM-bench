"""Phase 2A: 3 x 2 start-state design, simulation part.

{uniform, ansatz + Hadamard diffusion (mismatched), ansatz + matched diffusion}
  x {noiseless, FakeMarrakesh noise model}
  x M in {1,2,3,4}  x  r in 0..(r_opt+2),   N = 32, 8192 shots.

r_opt is the uniform-start value for that M, so every start state is read on the same r grid. The
marked set is the first M weight-2 basis states, as in the other sparse-regime experiments.

Noiseless: exact statevector probabilities (no shot noise), 30 ansatz seeds, so the distribution
over random ansatz angles is reported (median, IQR, min, max), not only seed 42.
FakeMarrakesh: one 8192-shot run per ansatz seed (default 6 seeds because each noisy run of these
deeper circuits takes tens of seconds; raise --noisy-seeds to extend, the script resumes from the
saved file). The uniform start is not re-run: its noisy curve is the 5-repeat result already in
results/sim/sparse_table_sim.json.

"Flat" is defined before looking at the data as: max over the r grid minus min over the r grid is
below 0.10 for that (start, M), taken on the median curve across seeds.

    python analysis/start_state_design.py --noiseless-seeds 30 --noisy-seeds 6
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

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
N = 5
FLAT_RANGE = 0.10
STARTS = [("ansatz_hadamard", "ansatz", "hadamard"), ("ansatz_matched", "ansatz", "matched")]


def marked_set(M):
    return [i for i in range(2**N) if bin(i).count("1") == 2][:M]


def summarize(values):
    v = np.asarray(values, float)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"median": float(med), "q1": float(q1), "q3": float(q3), "min": float(v.min()),
            "max": float(v.max()), "n": int(len(v))}


def noiseless_part(n_seeds):
    rows = []
    for M in (1, 2, 3, 4):
        r_grid = range(0, optimal_iterations(M, 2**N) + 3)
        marked = marked_set(M)
        for r in r_grid:
            uni = exact_success_probability(N, 0, r, initial_state="uniform", marked_states=marked)
            rows.append({"start": "uniform", "M": M, "r": r, "analytical": theoretical_success_probability(M, 2**N, r),
                         "summary": summarize([uni])})
            for name, init, diff in STARTS:
                vals = [exact_success_probability(N, 0, r, initial_state=init, seed=s,
                                                  marked_states=marked, diffusion=diff) for s in range(n_seeds)]
                rows.append({"start": name, "M": M, "r": r, "summary": summarize(vals), "values": vals})
    return rows


def flat_table(rows):
    out = []
    for start in ("uniform", "ansatz_hadamard", "ansatz_matched"):
        for M in (1, 2, 3, 4):
            med = [x["summary"]["median"] for x in rows if x["start"] == start and x["M"] == M]
            out.append({"start": start, "M": M, "median_range": max(med) - min(med),
                        "flat": (max(med) - min(med)) < FLAT_RANGE})
    return out


def noisy_part(n_seeds, shots, seed, saved):
    noisy = NoisySimulatorBackend(seed=seed, optimization_level=3)
    done = {(c["start"], c["M"], c["r"], c["ansatz_seed"]) for c in saved}
    for M in (1, 2, 3, 4):
        marked = marked_set(M)
        keys = {format(i, f"0{N}b") for i in marked}
        for r in range(0, optimal_iterations(M, 2**N) + 3):
            for name, init, diff in STARTS:
                for s in range(n_seeds):
                    if (name, M, r, s) in done:
                        continue
                    qc, _ = build_grover_circuit(N, 0, r, initial_state=init, seed=s,
                                                 marked_states=marked, diffusion=diff)
                    counts = noisy.run(qc, shots).counts
                    p = sum(c for k, c in counts.items() if k in keys) / shots
                    saved.append({"start": name, "M": M, "r": r, "ansatz_seed": s, "noisy_p": p,
                                  "counts": counts})
                    print(f"noisy {name} M={M} r={r} seed={s}: {p:.4f}", flush=True)
                    yield saved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--noiseless-seeds", type=int, default=30)
    ap.add_argument("--noisy-seeds", type=int, default=6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--skip-noisy", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    path = OUT / "start_state_design.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if "noiseless" not in data or data.get("noiseless_seeds") != args.noiseless_seeds:
        data["noiseless_seeds"] = args.noiseless_seeds
        data["noiseless"] = noiseless_part(args.noiseless_seeds)
        data["flat_table_noiseless"] = flat_table(data["noiseless"])
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        for row in data["flat_table_noiseless"]:
            print("noiseless flat?", row, flush=True)

    if not args.skip_noisy:
        saved = data.setdefault("noisy", [])
        for i, _ in enumerate(noisy_part(args.noisy_seeds, args.shots, args.seed, saved)):
            if i % 5 == 0:
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        data["noisy_seeds"] = args.noisy_seeds
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    write_experiment_manifest(str(OUT / "start_state_design_manifest.json"),
                              {"noiseless_seeds": args.noiseless_seeds, "noisy_seeds": args.noisy_seeds,
                               "seed": args.seed, "shots": args.shots, "flat_range_definition": FLAT_RANGE,
                               "script": "analysis/start_state_design.py"}, overwrite=True)


if __name__ == "__main__":
    main()
