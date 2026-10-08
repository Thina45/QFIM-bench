"""Phase 2C applied: effective fidelity per two-qubit gate from the simulated feasibility sweep.

For each (n, M, oracle style), fit p(g) = f^g p_ideal + (1 - f^g) p_noise with g the transpiled
two-qubit-gate count of the circuit at each r (binomial maximum likelihood, 300-draw parametric
bootstrap for the 95% interval). Each r contributes all 5 repeats pooled (5 x 8192 shots).

Reading the output: f is a per-two-qubit-gate fidelity, so f^g at the operating point is the
fraction of the ideal signal surviving; "signal at r_opt" is f^g(r_opt). n = 2 is skipped: with
M/N = 1/4 the ideal curve returns to the noise-free value at every even r, so f is not
identifiable from it. This is a fit to a SIMULATED noise model, not to hardware.

    python analysis/fidelity_decay_fit.py
"""

import json
from pathlib import Path

from qfim_bench.fit import fit_fidelity_decay
from qfim_bench.manifest import write_experiment_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"


def main() -> None:
    d = json.loads((OUT / "feasibility_sweep.json").read_text(encoding="utf-8"))
    shots = d["shots"] * len(d["repeat_seeds"])
    groups: dict = {}
    for p in d["points"]:
        groups.setdefault((p["n"], p["M"], p["style"]), []).append(p)
    rows = []
    for (n, M, style), pts in groups.items():
        if n == 2:
            continue
        g = [p["transpiled_two_qubit_gates"] for p in pts]
        ideal = [p["analytical"] for p in pts]
        k = [round(p["noisy_mean"] * shots) for p in pts]
        fit = fit_fidelity_decay(g, ideal, k, [shots] * len(pts), n_bootstrap=300, seed=1)
        r_opt = pts[0]["r_opt"]
        g_opt = next(p["transpiled_two_qubit_gates"] for p in pts if p["r"] == r_opt)
        rows.append({"n": n, "M": M, "style": style, "f_per_2q_gate": fit.f, "f_ci95": fit.f_ci,
                     "p_noise": fit.p_noise, "p_noise_ci95": fit.p_noise_ci, "M_over_N": M / 2**n,
                     "signal_surviving_at_r_opt": fit.f**g_opt, "two_qubit_gates_at_r_opt": g_opt})
        print(f"n={n} M={M} {style:11s} f={fit.f:.5f} [{fit.f_ci[0]:.5f},{fit.f_ci[1]:.5f}]  "
              f"p_noise={fit.p_noise:.3f} (M/N={M / 2**n:.3f})  signal at r_opt {fit.f**g_opt:.2f}")
    (OUT / "fidelity_decay_fit.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_experiment_manifest(str(OUT / "fidelity_decay_fit_manifest.json"),
                              {"script": "analysis/fidelity_decay_fit.py", "source": "feasibility_sweep.json"}, overwrite=True)


if __name__ == "__main__":
    main()
