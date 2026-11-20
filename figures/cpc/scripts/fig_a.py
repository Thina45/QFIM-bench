"""Fig. A: ladder success probability vs r, three panels (n=3,4,5) -- ideal, FakeMarrakesh
prediction, hardware (2026-10-08, one sitting; no replication days available yet), and the
classical query baseline (dashed). Reads results/cpc_revision/phase1a_classical_baseline.csv and
review/preregistration/ladder_predictions.json; writes figures/cpc/fig_a.{pdf,png}.

    python figures/cpc/scripts/fig_a.py
"""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

PRED = {c["id"]: c for c in json.loads((ROOT / "review" / "preregistration" / "ladder_predictions.json").read_text())["circuits"]}
TIER_N = {"A": 3, "B": 4, "C": 5}
TIER_M = {"A": 1, "B": 2, "C": 4}


def load_phase1a():
    with (ROOT / "results" / "cpc_revision" / "phase1a_classical_baseline.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    rows = load_phase1a()
    fig, axes = plt.subplots(1, 3, figsize=(190 / 25.4, 60 / 25.4), sharey=True)
    for ax, tier in zip(axes, ["A", "B", "C"]):
        n, M = TIER_N[tier], TIER_M[tier]
        trow = [r for r in rows if r["tier"] == tier]
        trow.sort(key=lambda r: int(r["r"]))
        rs = [int(r["r"]) for r in trow]
        hw = [float(r["hw_mean"]) for r in trow]
        lo = [float(r["hw_mean"]) - float(r["hw_t_ci95_lo"]) for r in trow]
        hi = [float(r["hw_t_ci95_hi"]) - float(r["hw_mean"]) for r in trow]
        pc = [float(r["classical_Pc"]) for r in trow]
        ideal = [PRED[f"ladder_n{n}_M{M}_r{r}"]["ideal"] for r in rs]
        pred = [PRED[f"ladder_n{n}_M{M}_r{r}"]["prediction"] for r in rs]

        ax.plot(rs, ideal, "-", color="0.3", label="ideal (Eq. 1)")
        ax.plot(rs, pred, "s--", label="FakeMarrakesh")
        ax.errorbar(rs, hw, yerr=[lo, hi], fmt="o-", label="hardware (Oct 8)")
        ax.plot(rs, pc, ":", color="0.5", label="classical baseline")
        ax.set_xlabel("Grover iterations r")
        ax.set_xticks(rs)
        ax.annotate(f"n={n}, M={M}", xy=(0.97, 0.95), xycoords="axes fraction", ha="right", va="top", fontsize=7.5)
    axes[0].set_ylabel("marked-state probability")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=4, columnspacing=1.2, fontsize=7.5)

    fig.savefig(FIG / "fig_a.pdf")
    fig.savefig(FIG / "fig_a.png")  # 300 dpi from savefig.dpi in cpc.mplstyle
    print("wrote", FIG / "fig_a.pdf", "and .png")


if __name__ == "__main__":
    main()
