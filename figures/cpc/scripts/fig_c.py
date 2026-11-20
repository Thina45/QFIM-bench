"""Fig. C: two panels. (a) marked-state probability vs two-qubit gate count (log x-axis), hardware
points + fitted depolarizing model curves, per size n=3,4,5. (b) per-size Grover-fit f vs the
EXPLORATORY echo-derived f, both with sqrt(reduced chi-square)-inflated 95% CIs.
Reads results/cpc_revision/phase1a_classical_baseline.csv, phase1b_global_fit.json,
phase1c_echo_vs_grover_fit.csv, and review/preregistration/ladder_predictions.json for the 2Q gate
counts actually used per circuit. Writes figures/cpc/fig_c.{pdf,png}.

    python figures/cpc/scripts/fig_c.py
"""

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

PRED = {c["id"]: c for c in json.loads((ROOT / "review" / "preregistration" / "ladder_predictions.json").read_text())["circuits"]}
TIER_N = {"A": 3, "B": 4, "C": 5}
TIER_M = {"A": 1, "B": 2, "C": 4}
TIER_COLOR = {"A": "#0072B2", "B": "#D55E00", "C": "#009E73"}


def decay_model(g, f, p_noise, p_ideal):
    w = f**np.asarray(g, float)
    return w * p_ideal + (1 - w) * p_noise


def inflate(ci, f, reduced_chi2):
    scale = math.sqrt(reduced_chi2) if reduced_chi2 and reduced_chi2 > 0 else 1.0
    return [f - (f - ci[0]) * scale, f + (ci[1] - f) * scale]


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1a_classical_baseline.csv").open(encoding="utf-8") as f:
        rows_a = list(csv.DictReader(f))
    fit = json.loads((ROOT / "results" / "cpc_revision" / "phase1b_global_fit.json").read_text())
    with (ROOT / "results" / "cpc_revision" / "phase1c_echo_vs_grover_fit.csv").open(encoding="utf-8") as f:
        rows_c = list(csv.DictReader(f))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(190 / 25.4, 62 / 25.4))

    # (a) success probability vs two-qubit gate count, log x
    for tier in ["A", "B", "C"]:
        n, M = TIER_N[tier], TIER_M[tier]
        color = TIER_COLOR[tier]
        trow = sorted([r for r in rows_a if r["tier"] == tier], key=lambda r: int(r["r"]))
        gates = np.array([PRED[f"ladder_n{n}_M{M}_r{int(r['r'])}"]["two_qubit_gates"] for r in trow])
        hw = np.array([float(r["hw_mean"]) for r in trow])
        ax.scatter(np.maximum(gates, 1), hw, marker="o", color=color, label=f"n={n}")
        gmin = max(gates[gates > 0].min() if (gates > 0).any() else 1, 1)
        g_line = np.geomspace(gmin, max(gates.max(), gmin + 1), 200)
        ideals = np.array([PRED[f"ladder_n{n}_M{M}_r{int(r['r'])}"]["ideal"] for r in trow])
        ideal_interp = np.interp(g_line, np.maximum(gates, 1), ideals)
        model = decay_model(g_line, fit["per_size"][tier]["f"], fit["per_size"][tier]["p_noise"], ideal_interp)
        ax.plot(g_line, model, "-", color=color, alpha=0.7, linewidth=0.9)
    ax.set_xscale("log")
    ax.set_xlabel("two-qubit gate count")
    ax.set_ylabel("marked-state probability")
    ax.legend(loc="upper right", fontsize=7)
    ax.set_title("(a)")

    # (b) per-size Grover fit f vs echo-derived f, inflated CIs
    xs = np.arange(len(rows_c))
    grover_f, grover_lo, grover_hi = [], [], []
    echo_f, echo_lo, echo_hi = [], [], []
    for r in rows_c:
        tier = r["tier"]
        pf = fit["per_size"][tier]
        g_ci = inflate(pf["f_ci95"], pf["f"], pf["reduced_chi_square"])
        grover_f.append(pf["f"]); grover_lo.append(pf["f"] - g_ci[0]); grover_hi.append(g_ci[1] - pf["f"])
        f_echo = float(r["f_echo"])
        echo_f.append(f_echo)
        echo_lo.append(f_echo - float(r["f_echo_ci95_lo"]))
        echo_hi.append(float(r["f_echo_ci95_hi"]) - f_echo)

    dx = 0.15
    ax2.errorbar(xs - dx, grover_f, yerr=[grover_lo, grover_hi], fmt="o", color="#0072B2",
                 label="Grover fit $f$ (per size)", capsize=2)
    ax2.errorbar(xs + dx, echo_f, yerr=[echo_lo, echo_hi], fmt="^", color="#D55E00",
                 label="echo (exploratory)", capsize=2)
    ax2.set_xticks(xs)
    ax2.set_xticklabels([f"n={r['n']}" for r in rows_c])
    ax2.set_ylabel("effective fidelity per two-qubit gate $f$")
    ax2.legend(loc="lower left", fontsize=7)
    ax2.set_title("(b)")

    fig.savefig(FIG / "fig_c.pdf")
    fig.savefig(FIG / "fig_c.png")
    print("wrote", FIG / "fig_c.pdf", "and .png")
    for tier in ["A", "B", "C"]:
        pf = fit["per_size"][tier]
        ci = inflate(pf["f_ci95"], pf["f"], pf["reduced_chi_square"])
        print(f"n={TIER_N[tier]}: f={pf['f']:.5f} inflated CI=[{ci[0]:.5f},{ci[1]:.5f}] "
              f"reduced_chi2={pf['reduced_chi_square']:.1f}")
    g = fit["global"]
    gci = inflate(g["f_ci95"], g["f"], g["reduced_chi_square"])
    print(f"global: f={g['f']:.5f} inflated CI=[{gci[0]:.5f},{gci[1]:.5f}] "
          f"reduced_chi2={g['reduced_chi_square']:.1f}")


if __name__ == "__main__":
    main()
