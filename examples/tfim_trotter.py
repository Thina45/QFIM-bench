"""examples/tfim_trotter.py: a second non-Grover example of Layer A's generality (item 6 of the
CPC v4 pass). First-order Trotterized time evolution of the 1D transverse-field Ising model
(H = -J sum Z_i Z_{i+1} - h sum X_i), n=4..6 qubits, 1-4 Trotter steps, starting from |0...0>.
"Success" is the Loschmidt-echo-style return probability P(measure all-zeros). Runs each (n,
steps) point on SimulatorBackend (ideal, noiseless statevector of the SAME trotterized circuit --
matching the Grover ladder's own convention: p_ideal is the noiseless probability of the actual
circuit executed, not an idealized continuous-time target) and NoisySimulatorBackend (ibm_marrakesh
calibration-snapshot noise model), then applies noise_analysis.compare_distributions,
reproducibility.repeated_run_check (5 seeds) and fit.fit_fidelity_decay vs two-qubit gate count
(post-transpile RZZ-chain two-qubit gates, read from NoisySimulatorBackend.transpile()).

No hardware job is submitted; everything here is simulated.

    python examples/tfim_trotter.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qfim_bench.backends import NoisySimulatorBackend, SimulatorBackend  # noqa: E402
from qfim_bench.fit import fit_fidelity_decay  # noqa: E402
from qfim_bench.noise_analysis import compare_distributions  # noqa: E402
from qfim_bench.reproducibility import repeated_run_check  # noqa: E402

OUT = ROOT / "results" / "cpc_v4"
OUT.mkdir(parents=True, exist_ok=True)
SHOTS = 8192
SEEDS = [0, 1, 2, 3, 4]
J, H_FIELD, DT = 1.0, 1.0, 0.2


def tfim_circuit(n: int, steps: int) -> QuantumCircuit:
    qc = QuantumCircuit(n, n, name=f"tfim_n{n}_s{steps}")
    for _ in range(steps):
        for i in range(n - 1):
            qc.rzz(2 * J * DT, i, i + 1)
        for i in range(n):
            qc.rx(2 * H_FIELD * DT, i)
    qc.measure(range(n), range(n))
    return qc


def return_probability(result, n: int) -> float:
    zeros = "0" * n
    return result.counts.get(zeros, 0) / result.shots


def ideal_return_probability(qc: QuantumCircuit, n: int) -> float:
    ideal = SimulatorBackend()
    res = ideal.run(qc, shots=8192 * 4)
    return return_probability(res, n)


def main() -> None:
    rows = []
    g_list, ideal_list, k_list, n_list = [], [], [], []
    for n in range(4, 7):
        for steps in range(1, 5):
            qc = tfim_circuit(n, steps)
            noisy_backend = NoisySimulatorBackend(fake_backend_name="FakeMarrakesh", seed=42,
                                                    optimization_level=3)
            tq = noisy_backend.transpile(qc)
            g = sum(v for k_, v in tq.count_ops().items() if k_ in ("cz", "ecr", "cx"))

            p_ideal = ideal_return_probability(qc, n)

            ideal_backend = SimulatorBackend()
            comparisons = compare_distributions(qc, {"ideal": ideal_backend, "noisy": noisy_backend},
                                                  shots=SHOTS)
            tvd_cmp = next(c for c in comparisons if {c.backend_a_name, c.backend_b_name} == {"ideal", "noisy"})

            repro = repeated_run_check(qc, noisy_backend, n_runs=len(SEEDS), shots=SHOTS,
                                        metric_fn=lambda r: return_probability(r, n))

            noisy_result = noisy_backend.run(qc, SHOTS)
            k = int(round(return_probability(noisy_result, n) * SHOTS))

            rows.append({
                "n": n, "steps": steps, "two_qubit_gates": g, "ideal_return_probability": p_ideal,
                "noisy_return_probability": return_probability(noisy_result, n),
                "tvd_ideal_vs_noisy": tvd_cmp.tvd.point_estimate,
                "repeated_run_mean": repro.summary.mean, "repeated_run_sd": repro.summary.sd,
                "repeated_run_cv_pct": repro.summary.cv_percent,
                "repeated_run_ci95": [repro.summary.ci_low, repro.summary.ci_high],
            })
            g_list.append(g); ideal_list.append(p_ideal); k_list.append(k); n_list.append(SHOTS)
            print(f"n={n} steps={steps}: g={g} p_ideal={p_ideal:.4f} "
                  f"noisy={rows[-1]['noisy_return_probability']:.4f}")

    fit = fit_fidelity_decay(g_list, ideal_list, k_list, n_list, n_bootstrap=300, seed=1)
    out = {"rows": rows, "fit": {"f": fit.f, "f_ci95": list(fit.f_ci), "p_noise": fit.p_noise,
                                  "p_noise_ci95": list(fit.p_noise_ci)},
           "params": {"J": J, "h": H_FIELD, "dt": DT},
           "note": "success = P(measure all-zeros), a Loschmidt-echo-style return probability; "
                   "p_ideal is the noiseless statevector probability of the SAME trotterized "
                   "circuit (matching the Grover ladder's own p_ideal convention), not the exact "
                   "continuous-time Hamiltonian evolution"}
    (OUT / "tfim_trotter.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("fit f:", fit.f, "CI:", fit.f_ci)
    print(f"wrote {OUT / 'tfim_trotter.json'}")


if __name__ == "__main__":
    main()
