"""Fig. N: output distributions over ALL basis states, two rows -- n=3 r=2 (top) and n=5 r=1
(bottom) -- each with three bars per basis state: ideal (statevector), FakeMarrakesh (noisy
simulator, same optimization_level/seed_transpiler/seeds as the original predictions,
analysis/ladder_predictions.py), and measured hardware (2026-10-08, one repeat: day1.json for
n=3, C_run1.json for n=5). Marked states highlighted (red outline). TVD and Hellinger values
(hardware vs ideal / vs FakeMarrakesh) are annotated in captions.md, not in the image, from
results/cpc_revision/phase1d_distances.csv.

    python figures/cpc/scripts/fig_n.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in, panel_label  # noqa: E402

from qfim_bench.backends import NoisySimulatorBackend  # noqa: E402
from qfim_bench.circuit import build_grover_circuit  # noqa: E402

SEED = 42
SHOTS = 8192
CASES = [
    {"n": 3, "M": 1, "r": 2, "marked": [3], "hw_file": "results/hardware/ladder_v2/day1.json",
     "cid": "ladder_n3_M1_r2"},
    {"n": 5, "M": 4, "r": 1, "marked": [i for i in range(32) if bin(i).count("1") == 2][:4],
     "hw_file": "results/hardware/ladder_v2b/C_run1.json", "cid": "ladder_n5_M4_r1"},
]


def ideal_probs(n, marked, qc):
    from qiskit.quantum_info import Statevector
    qc_sv = qc.remove_final_measurements(inplace=False)
    sv = Statevector.from_instruction(qc_sv)
    probs = sv.probabilities()
    return probs


def fakemarrakesh_probs(qc, n):
    noisy = NoisySimulatorBackend(seed=SEED, optimization_level=3)
    fake = FakeMarrakesh()
    t = transpile(qc, fake, optimization_level=3, seed_transpiler=SEED)
    seeds = [SEED + 100 + k for k in range(5)]
    reps = noisy.sample(t, SHOTS, seeds)
    counts = {}
    for rep in reps:
        for k, v in rep.counts.items():
            counts[k] = counts.get(k, 0) + v
    total = sum(counts.values())
    probs = np.zeros(2**n)
    for bitstr, c in counts.items():
        probs[int(bitstr, 2)] += c / total
    return probs


def hw_probs(path, cid, n):
    d = json.loads((ROOT / path).read_text(encoding="utf-8"))
    counts = d["counts"][cid]
    total = sum(counts.values())
    probs = np.zeros(2**n)
    for bitstr, c in counts.items():
        probs[int(bitstr, 2)] += c / total
    return probs


def main():
    fig, axes = plt.subplots(2, 1, figsize=mm2in(190, 110))
    panel_labels = ["(a)", "(b)"]
    for ax, case, lab in zip(axes, CASES, panel_labels):
        n, M, r, marked = case["n"], case["M"], case["r"], case["marked"]
        qc, info = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked,
                                         oracle_style="mcz", seed=SEED)
        ideal = ideal_probs(n, marked, qc)
        fm = fakemarrakesh_probs(qc, n)
        hw = hw_probs(case["hw_file"], case["cid"], n)

        N = 2**n
        xs = np.arange(N)
        w = 0.26
        ax.bar(xs - w, ideal, width=w, color="0.3", label="ideal")
        ax.bar(xs, fm, width=w, color="#0072B2", label="FakeMarrakesh")
        ax.bar(xs + w, hw, width=w, color="#D55E00", label="hardware (Oct 8)")
        for m_idx in marked:
            ax.axvspan(m_idx - 0.5, m_idx + 0.5, color="#D55E00", alpha=0.12, zorder=0)
        if N <= 16:
            ax.set_xticks(xs)
            ax.set_xticklabels([format(i, f"0{n}b") for i in xs], fontsize=5.5, rotation=90)
        else:
            step = 4
            ax.set_xticks(xs[::step])
            ax.set_xticklabels([format(i, f"0{n}b") for i in xs[::step]], fontsize=5, rotation=90)
        ax.set_ylabel("probability")
        ax.set_xlabel("basis state")
        panel_label(ax, lab)
        ax.text(0.98, 0.92, f"n={n}, M={M}, r={r}", transform=ax.transAxes, ha="right", va="top",
                fontsize=7)

    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="outside upper center", ncol=3, fontsize=7.5)

    save_all(fig, "fig_n")


if __name__ == "__main__":
    main()
