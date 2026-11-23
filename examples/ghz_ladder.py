"""examples/ghz_ladder.py: a non-Grover example of Layer A's generality (item 6 of the CPC v4
pass). Builds a GHZ state |0...0> + |1...1> for n=3..6 qubits (H on qubit 0, then a CNOT chain),
runs it on SimulatorBackend (ideal) and NoisySimulatorBackend (ibm_marrakesh calibration-snapshot
noise model, saved Oct-8 snapshot), and applies the SAME Layer A tools the Grover ladder campaigns
use: noise_analysis.compare_distributions (TVD/Hellinger, ideal vs noisy), reproducibility.
repeated_run_check (5 simulator seeds), and fit.fit_fidelity_decay (success probability vs
two-qubit gate count, here n-1 CNOTs for an n-qubit GHZ state).

"Success" here is measuring either all-zeros or all-ones (the two GHZ-correct outcomes); its
ideal probability is exactly 1.0 at every n (a noiseless GHZ circuit always returns one of the two
basis states), so the two-qubit-gate-count decay this fits is a genuine fidelity-vs-system-size
curve, not confounded by a varying ideal target the way the Grover ladder's p_ideal(r) is.

No hardware job is submitted; everything here is simulated (ideal statevector + the saved
calibration-snapshot noise model).

    python examples/ghz_ladder.py
"""
import json
import sys
from pathlib import Path

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


def ghz_circuit(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n, n, name=f"ghz_{n}")
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n), range(n))
    return qc


def ghz_success(result) -> float:
    zeros, ones = "0" * (len(next(iter(result.counts))) if result.counts else 0), None
    n = len(next(iter(result.counts)))
    zeros, ones = "0" * n, "1" * n
    hit = sum(c for b, c in result.counts.items() if b in (zeros, ones))
    return hit / result.shots


def main() -> None:
    rows = []
    g_list, ideal_list, k_list, n_list = [], [], [], []
    for n in range(3, 7):
        qc = ghz_circuit(n)
        g = n - 1  # two-qubit gate count (CNOT chain)

        ideal_backend = SimulatorBackend()
        noisy_backend = NoisySimulatorBackend(fake_backend_name="FakeMarrakesh", seed=42, optimization_level=3)

        comparisons = compare_distributions(qc, {"ideal": ideal_backend, "noisy": noisy_backend}, shots=SHOTS)
        tvd_cmp = next(c for c in comparisons if {c.backend_a_name, c.backend_b_name} == {"ideal", "noisy"})

        repro = repeated_run_check(qc, noisy_backend, n_runs=len(SEEDS), shots=SHOTS,
                                    metric_fn=ghz_success)

        noisy_result = noisy_backend.run(qc, SHOTS)
        k = int(round(ghz_success(noisy_result) * SHOTS))

        rows.append({
            "n": n, "two_qubit_gates": g, "ideal_success_probability": 1.0,
            "noisy_success_probability": ghz_success(noisy_result),
            "tvd_ideal_vs_noisy": tvd_cmp.tvd.point_estimate,
            "repeated_run_mean": repro.summary.mean, "repeated_run_sd": repro.summary.sd,
            "repeated_run_cv_pct": repro.summary.cv_percent,
            "repeated_run_ci95": [repro.summary.ci_low, repro.summary.ci_high],
        })
        g_list.append(g); ideal_list.append(1.0); k_list.append(k); n_list.append(SHOTS)
        print(f"n={n}: g={g} success={rows[-1]['noisy_success_probability']:.4f} "
              f"TVD(ideal,noisy)={rows[-1]['tvd_ideal_vs_noisy']:.4f}")

    fit = fit_fidelity_decay(g_list, ideal_list, k_list, n_list, n_bootstrap=300, seed=1)
    out = {"rows": rows, "fit": {"f": fit.f, "f_ci95": list(fit.f_ci), "p_noise": fit.p_noise,
                                  "p_noise_ci95": list(fit.p_noise_ci)},
           "note": "success = measure all-zeros or all-ones; ideal_success_probability is exactly "
                   "1.0 at every n (noiseless GHZ always returns one of the two basis states)"}
    (OUT / "ghz_ladder.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("fit f:", fit.f, "CI:", fit.f_ci)
    print(f"wrote {OUT / 'ghz_ladder.json'}")


if __name__ == "__main__":
    main()
