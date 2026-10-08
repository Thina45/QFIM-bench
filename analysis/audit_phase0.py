"""Phase 0 audit experiments (no hardware, no circuit changes).

Answers, numerically, the questions in review/AUDIT.md:
  A. Is build_diffusion() the Hadamard reflection about the uniform state?
  B. Does build_grover_circuit() use that same diffusion for initial_state="ansatz"?
  C. What would a diffusion matched to the ansatz state do (A S0 A^dagger)?
  D. Is the item <-> qubit <-> bitstring-character ordering consistent?
  E. (--noisy) Reproduce Table 2 on the noiseless and FakeMarrakesh simulators.

    python analysis/audit_phase0.py --seed 42            # fast, exact statevector parts
    python analysis/audit_phase0.py --seed 42 --noisy    # adds the slow sampled/noisy part

Outputs: results/sim/audit_phase0.json (+ manifest). Raw counts are saved for E.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import efficient_su2
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator

from qfim_bench.circuit import (
    bind_parameters,
    build_diffusion,
    build_grover_circuit,
    count_marked_states,
    theoretical_success_probability,
)
from qfim_bench.encoding import decode_bitstring_to_itemset
from qfim_bench.manifest import write_experiment_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
N_QUBITS = 5
N = 2**N_QUBITS


def hamming_marked(threshold: int = 2) -> np.ndarray:
    return np.array([bin(i).count("1") >= threshold for i in range(N)])


def ansatz_unitary(seed: int) -> np.ndarray:
    circ = efficient_su2(N_QUBITS, entanglement="linear", reps=1).decompose()
    circ = bind_parameters(circ, seed=seed)
    return Operator(circ).data


def evolve(psi0, marked, diffusion, r_max):
    """P(marked) for r = 0..r_max under (D O)^r applied to psi0."""
    oracle = np.diag(np.where(marked, -1.0, 1.0))
    psi = psi0.copy()
    probs = [float(np.sum(np.abs(psi[marked]) ** 2))]
    for _ in range(r_max):
        psi = diffusion @ (oracle @ psi)
        probs.append(float(np.sum(np.abs(psi[marked]) ** 2)))
    return probs


def check_diffusion_is_uniform_reflection() -> dict:
    d_circ = Operator(build_diffusion(N_QUBITS)).data
    s = np.ones(N) / math.sqrt(N)
    d_ref = 2.0 * np.outer(s, s) - np.eye(N)
    phase = d_circ[0, 0] / d_ref[0, 0]
    err = float(np.max(np.abs(d_circ - phase * d_ref)))
    return {"max_abs_error_up_to_global_phase": err, "global_phase": [phase.real, phase.imag]}


def check_package_matches_model(seed: int, r_max: int = 4) -> dict:
    """Exact statevector of the package's real circuit vs the numpy model with Hadamard diffusion."""
    marked = hamming_marked(2)
    s = np.ones(N) / math.sqrt(N)
    d_h = 2.0 * np.outer(s, s) - np.eye(N)
    out = {}
    for init in ("uniform", "ansatz"):
        a = ansatz_unitary(seed)
        psi0 = s.astype(complex) if init == "uniform" else a[:, 0]
        model = evolve(psi0, marked, d_h, r_max)
        pkg = []
        for r in range(r_max + 1):
            qc, _ = build_grover_circuit(N_QUBITS, 2, r, initial_state=init, seed=seed, measure=False)
            probs = Statevector.from_instruction(qc).probabilities_dict(qargs=list(range(N_QUBITS)))
            pkg.append(float(sum(p for b, p in probs.items() if b.count("1") >= 2)))
        out[init] = {
            "model_hadamard_diffusion": model,
            "package_circuit": pkg,
            "max_abs_diff": float(max(abs(m - p) for m, p in zip(model, pkg))),
        }
    return out


def diffusion_variants(seed: int, marked: np.ndarray, r_max: int = 5) -> dict:
    s = np.ones(N) / math.sqrt(N)
    d_h = 2.0 * np.outer(s, s) - np.eye(N)
    a = ansatz_unitary(seed)
    psi_a = a[:, 0]
    d_m = 2.0 * np.outer(psi_a, psi_a.conj()) - np.eye(N)
    p_a = float(np.sum(np.abs(psi_a[marked]) ** 2))
    theta_a = math.asin(math.sqrt(p_a))
    M = int(marked.sum())
    theta_u = math.asin(math.sqrt(M / N))
    return {
        "M": M,
        "P_A_marked": p_a,
        "theta_A": theta_a,
        "uniform_hadamard": evolve(s.astype(complex), marked, d_h, r_max),
        "uniform_theory": [math.sin((2 * r + 1) * theta_u) ** 2 for r in range(r_max + 1)],
        "ansatz_hadamard_current": evolve(psi_a, marked, d_h, r_max),
        "ansatz_matched": evolve(psi_a, marked, d_m, r_max),
        "ansatz_matched_theory": [math.sin((2 * r + 1) * theta_a) ** 2 for r in range(r_max + 1)],
    }


def ordering_experiment() -> dict:
    """Flip qubit 0 only, measure qubit i -> clbit i, and decode with the package's decoder."""
    order = [f"item_{i}" for i in range(N_QUBITS)]
    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    qc.x(0)
    qc.measure(range(N_QUBITS), range(N_QUBITS))
    counts = AerSimulator(seed_simulator=1).run(qc, shots=64).result().get_counts()
    key = next(iter(counts))
    decoded = sorted(decode_bitstring_to_itemset(key, order))
    return {
        "flipped_qubit": 0,
        "qiskit_count_key": key,
        "decoded_by_package": decoded,
        "oracle_convention_expects": ["item_0"],
        "consistent": decoded == ["item_0"],
    }


def table2_reproduction(seed: int, shots: int, noisy: bool) -> dict:
    out = {"analytical_M26_N32": {r: theoretical_success_probability(26, 32, r) for r in range(0, 5)}}
    out["analytical_M26_N32"][0] = 26 / 32
    sim = AerSimulator(seed_simulator=seed)
    noiseless = {}
    for r in range(0, 5):
        qc, _ = build_grover_circuit(N_QUBITS, 2, r, initial_state="uniform", seed=seed)
        counts = sim.run(qc, shots=shots).result().get_counts()
        noiseless[r] = counts
    out["noiseless_counts"] = noiseless
    out["noiseless_p"] = {
        r: sum(c for b, c in cts.items() if b.count("1") >= 2) / shots for r, cts in noiseless.items()
    }
    if noisy:
        from qfim_bench.backends import NoisySimulatorBackend

        nz = {}
        for r in range(0, 5):
            qc, _ = build_grover_circuit(N_QUBITS, 2, r, initial_state="uniform", seed=seed)
            nz[r] = NoisySimulatorBackend(seed=seed, optimization_level=1).run(qc, shots=shots).counts
        out["noisy_counts"] = nz
        out["noisy_p"] = {r: sum(c for b, c in cts.items() if b.count("1") >= 2) / shots for r, cts in nz.items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--shots", type=int, default=8192)
    ap.add_argument("--noisy", action="store_true", help="also run the slow FakeMarrakesh sampling")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    sparse = np.zeros(N, dtype=bool)
    sparse[rng.choice(N, size=3, replace=False)] = True

    result = {
        "seed": args.seed,
        "A_diffusion_is_uniform_reflection": check_diffusion_is_uniform_reflection(),
        "B_package_vs_numpy_model": check_package_matches_model(args.seed),
        "C_variants_M26_hamming": diffusion_variants(args.seed, hamming_marked(2)),
        "C_variants_M3_sparse": diffusion_variants(args.seed, sparse),
        "C_sparse_marked_indices": [int(i) for i in np.flatnonzero(sparse)],
        "D_ordering": ordering_experiment(),
        "E_table2": table2_reproduction(args.seed, args.shots, args.noisy),
    }
    name = "audit_phase0_noisy.json" if args.noisy else "audit_phase0.json"
    (OUT / name).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    write_experiment_manifest(
        str(OUT / name.replace(".json", "_manifest.json")),
        {"seed": args.seed, "shots": args.shots, "noisy": args.noisy, "script": "analysis/audit_phase0.py"},
        overwrite=True,
    )
    print("saved", OUT / name)


if __name__ == "__main__":
    main()
