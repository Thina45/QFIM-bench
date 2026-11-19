"""Fig. C: success probability vs two-qubit gate count with the fitted depolarizing curve (per-size
fit) and the EXPLORATORY echo-decay fidelity, annotated with fitted f and its 95% CI.
Reads results/cpc_revision/phase1a_classical_baseline.csv, phase1b_global_fit.json,
phase1c_echo_vs_grover_fit.csv, and review/preregistration/ladder_predictions.json for the 2Q gate
counts actually used per circuit. Writes figures/cpc/fig_c.{pdf,png}.

    python figures/cpc/scripts/fig_c.py
"""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

PRED = {c["id"]: c for c in json.loads((ROOT / "review" / "preregistration" / "ladder_predictions.json").read_text())["circuits"]}
TIER_N = {"A": 3, "B": 4, "C": 5}
TIER_M = {"A": 1, "B": 2, "C": 4}


def decay_model(g, f, p_noise, p_ideal):
    w = f**np.asarray(g, float)
    return w * p_ideal + (1 - w) * p_noise


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1a_classical_baseline.csv").open(encoding="utf-8") as f:
        rows_a = list(csv.DictReader(f))
    fit = json.loads((ROOT / "results" / "cpc_revision" / "phase1b_global_fit.json").read_text())
    with (ROOT / "results" / "cpc_revision" / "phase1c_echo_vs_grover_fit.csv").open(encoding="utf-8") as f:
        rows_c = list(csv.DictReader(f))

    fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
    for tier in ["A", "B", "C"]:
        n, M = TIER_N[tier], TIER_M[tier]
        trow = sorted([r for r in rows_a if r["tier"] == tier], key=lambda r: int(r["r"]))
        gates = np.array([PRED[f"ladder_n{n}_M{M}_r{int(r['r'])}"]["two_qubit_gates"] for r in trow])
        hw = np.array([float(r["hw_mean"]) for r in trow])
        p = ax.scatter(gates, hw, marker="o", label=f"hardware n={n} (fit f={fit['per_size'][tier]['f']:.4f})")
        g_line = np.linspace(0, gates.max(), 100)
        ideals = np.array([PRED[f"ladder_n{n}_M{M}_r{int(r['r'])}"]["ideal"] for r in trow])
        ideal_interp = np.interp(g_line, gates, ideals)
        model = decay_model(g_line, fit["per_size"][tier]["f"], fit["per_size"][tier]["p_noise"], ideal_interp)
        ax.plot(g_line, model, "-", color=p.get_facecolor()[0], alpha=0.6, linewidth=0.9)

    echo_colors = {"3": "0.3", "4": "0.5", "5": "0.7"}
    for r in rows_c:
        ax.scatter([float(r["echo_two_qubit_gates"])], [float(r["f_echo"])], marker="^",
                    color=echo_colors.get(r["n"], "0.4"),
                    label=f"EXPLORATORY echo f, n={r['n']}")

    ax.set_xlabel("two-qubit gate count")
    ax.set_ylabel("marked-state probability / fitted fidelity")
    ax.legend(loc="upper right", fontsize=6.5)
    ax.annotate(f"global fit f={fit['global']['f']:.5f}\nCI [{fit['global']['f_ci95'][0]:.5f}, {fit['global']['f_ci95'][1]:.5f}]",
                xy=(0.02, 0.02), xycoords="axes fraction", fontsize=7, va="bottom")

    fig.savefig(FIG / "fig_c.pdf")
    fig.savefig(FIG / "fig_c.png")
    print("wrote", FIG / "fig_c.pdf", "and .png")


if __name__ == "__main__":
    main()
