"""Predictions and cost estimates for the proposed hardware ladder (DRAFT; nothing is submitted).

Ladder (review/OPERATING_POINT_ADDENDUM.md): (n, M) in {(3,1), (4,2), (5,4)}, oracle style "mcz",
uniform start, matched diffusion, r = 0..r_opt+2, marked set = first M weight-2 basis states.
Controls per point: a depth-matched echo circuit at r_opt and a readout baseline per n.

Prediction for each ladder cell = the FakeMarrakesh (optimization level 3, 5 repeats, 8192 shots)
mean already computed in results/sim/feasibility_sweep.json, with a tolerance band

    half-width = 5 * sqrt(p (1 - p) / 8192)  +  MODEL_ALLOWANCE

where 5 sigma of shot noise covers sampling and MODEL_ALLOWANCE = 0.05 (absolute probability) is a
fixed, stated allowance for the simulator being one calibration snapshot of a drifting device. Both
numbers are set here, before any hardware data exist, and are not to be changed afterwards.

Echo: the logical circuit B (state preparation plus r_opt Grover iterations) followed by a barrier
and B^dagger, measured on the item qubits. Ideal outcome is all zeros with probability 1. The barrier
stops the transpiler cancelling B against B^dagger. Readout baseline: no gates (all zeros) and X on
every qubit (all ones), measured.

Per-circuit time estimate: transpile with ALAP scheduling against FakeMarrakesh (optimization level
3, seed_transpiler 42), take the scheduled duration, add REP_DELAY per shot. This is an estimate of
execution time only; IBM bills "quantum seconds" including per-job overhead that this script cannot
know, which is why Phase 3 measures one tiny job first.

    python analysis/ladder_predictions.py
"""

import json
import math
from pathlib import Path

from qiskit import QuantumCircuit, transpile

from qfim_bench.backends import NoisySimulatorBackend
from qfim_bench.circuit import build_grover_circuit, optimal_iterations
from qfim_bench.manifest import write_experiment_manifest

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "results" / "sim"
OUT = ROOT / "review" / "preregistration"
LADDER = [(3, 1), (4, 2), (5, 4)]
STYLE = "mcz"
SHOTS = 8192
MODEL_ALLOWANCE = 0.05
REP_DELAY = 250e-6  # seconds per shot; IBM's default repetition delay is of this order
SEED = 42


def marked_set(n, M):
    return [i for i in range(2**n) if bin(i).count("1") == 2][:M]


def band(p):
    return 5 * math.sqrt(p * (1 - p) / SHOTS) + MODEL_ALLOWANCE


def two_q(circ):
    return sum(v for k, v in circ.count_ops().items() if k in ("cz", "ecr", "cx"))


def echo_circuit(n, M, r):
    body, _ = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked_set(n, M),
                                   oracle_style=STYLE, measure=False)
    qc = QuantumCircuit(body.num_qubits, n)
    qc.compose(body, inplace=True)
    qc.barrier()
    qc.compose(body.inverse(), inplace=True)
    qc.measure(range(n), range(n))
    return qc


def readout_circuit(n, ones):
    qc = QuantumCircuit(n, n)
    if ones:
        qc.x(range(n))
    qc.measure(range(n), range(n))
    return qc


def main() -> None:
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

    OUT.mkdir(parents=True, exist_ok=True)
    sweep = json.loads((SIM / "feasibility_sweep.json").read_text(encoding="utf-8"))
    sim_cells = {(p["n"], p["M"], p["r"]): p for p in sweep["points"] if p["style"] == STYLE}
    fake = FakeMarrakesh()
    noisy = NoisySimulatorBackend(seed=SEED, optimization_level=3)
    seeds = [SEED + 100 + k for k in range(5)]

    def scheduled_seconds(circ):
        t = transpile(circ, fake, optimization_level=3, seed_transpiler=SEED, scheduling_method="alap")
        return t.estimate_duration(fake.target, unit="s"), two_q(t), t.depth()

    circuits = []
    for n, M in LADDER:
        r_opt = optimal_iterations(M, 2**n)
        for r in range(0, r_opt + 3):
            qc, info = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked_set(n, M),
                                            oracle_style=STYLE)
            cell = sim_cells[(n, M, r)]
            p = cell["noisy_mean"]
            dur, tq, depth = scheduled_seconds(qc)
            circuits.append({"id": f"ladder_n{n}_M{M}_r{r}", "kind": "ladder", "n": n, "M": M, "r": r, "r_opt": r_opt,
                             "marked": marked_set(n, M), "ideal": info.theoretical_p,
                             "prediction": p, "sim_sd": cell["noisy_sd"], "band_half_width": band(p),
                             "two_qubit_gates": tq, "depth": depth, "circuit_seconds_per_shot": dur})
        e = echo_circuit(n, M, r_opt)
        reps = noisy.run_repeats(e, SHOTS, seeds)
        p = sum(x.counts.get("0" * n, 0) for x in reps) / (SHOTS * len(reps))
        dur, tq, depth = scheduled_seconds(e)
        circuits.append({"id": f"echo_n{n}_M{M}_r{r_opt}", "kind": "echo", "n": n, "M": M, "r": r_opt,
                         "ideal": 1.0, "prediction": p, "band_half_width": band(p),
                         "two_qubit_gates": tq, "depth": depth, "circuit_seconds_per_shot": dur})
        print(f"echo n={n}: predicted P(all zeros) {p:.3f}, 2Q {tq}", flush=True)
        for ones in (False, True):
            rc = readout_circuit(n, ones)
            reps = noisy.run_repeats(rc, SHOTS, seeds)
            key = "1" * n if ones else "0" * n
            p = sum(x.counts.get(key, 0) for x in reps) / (SHOTS * len(reps))
            dur, tq, depth = scheduled_seconds(rc)
            circuits.append({"id": f"readout_n{n}_{'ones' if ones else 'zeros'}", "kind": "readout", "n": n,
                             "ideal": 1.0, "prediction": p, "band_half_width": band(p),
                             "two_qubit_gates": tq, "depth": depth, "circuit_seconds_per_shot": dur})

    for c in circuits:
        c["estimated_seconds_per_8192_shots"] = SHOTS * (c["circuit_seconds_per_shot"] + REP_DELAY)
    per_repeat = sum(c["estimated_seconds_per_8192_shots"] for c in circuits)
    result = {"style": STYLE, "shots": SHOTS, "model_allowance": MODEL_ALLOWANCE, "rep_delay_s": REP_DELAY,
              "circuits": circuits, "circuits_per_repeat": len(circuits),
              "estimated_execution_seconds_per_repeat": per_repeat}
    (OUT / "ladder_predictions.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_experiment_manifest(str(OUT / "ladder_predictions_manifest.json"),
                              {"script": "analysis/ladder_predictions.py", "seed": SEED}, overwrite=True)
    print(f"{len(circuits)} circuits per repeat; estimated execution time {per_repeat:.1f} s per repeat "
          f"({per_repeat / 60:.2f} min), excluding per-job overhead")


if __name__ == "__main__":
    main()
