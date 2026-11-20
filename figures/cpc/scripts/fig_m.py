"""Fig. M (EXPLORATORY -- marked in captions.md only, not in the image): ladder success
probability vs r for n=3,4,5, ibm_marrakesh Run 1 vs ibm_kingston Run 4, with the ideal curve and
the classical baseline. Reads results/cpc_revision/cpc_runs_analysis.json,
results/cpc_revision/cpc_run{1,4}_classical_baseline.csv, and
review/preregistration/ladder_predictions.json for the ideal curve.

    python figures/cpc/scripts/fig_m.py
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import DEVICE_COLOR, mm2in, panel_label  # noqa: E402

PRED = {c["id"]: c for c in json.loads((ROOT / "review" / "preregistration" / "ladder_predictions.json").read_text())["circuits"]}
TIER_N = {"A": 3, "B": 4, "C": 5}
TIER_M = {"A": 1, "B": 2, "C": 4}


def classical_by_r(campaign: str):
    with (ROOT / "results" / "cpc_revision" / f"{campaign}_classical_baseline.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {(r["tier"], int(r["r"])): float(r["classical_Pc"]) for r in rows}


def main():
    runs = json.loads((ROOT / "results" / "cpc_revision" / "cpc_runs_analysis.json").read_text())
    pc1 = classical_by_r("cpc_run1")

    fig, axes = plt.subplots(1, 3, figsize=mm2in(190, 62), sharey=True)
    labels = ["(a)", "(b)", "(c)"]
    for ax, tier, lab in zip(axes, ["A", "B", "C"], labels):
        n, M = TIER_N[tier], TIER_M[tier]
        rs = list(range(5))
        ideal = [PRED[f"ladder_n{n}_M{M}_r{r}"]["ideal"] for r in rs]
        pc = [pc1[(tier, r)] for r in rs]

        for campaign, device, color in [("cpc_run1", "ibm_marrakesh", DEVICE_COLOR["ibm_marrakesh"]),
                                         ("cpc_run4", "ibm_kingston", DEVICE_COLOR["ibm_kingston"])]:
            cells = runs[campaign][tier]
            means, los, his = [], [], []
            for r in rs:
                c = cells[f"ladder_n{n}_M{M}_r{r}"]
                means.append(c["mean"])
                los.append(c["mean"] - c["t_ci95"][0])
                his.append(c["t_ci95"][1] - c["mean"])
            ax.errorbar(rs, means, yerr=[los, his], fmt="o-", color=color,
                        label=f"{device} (Run {'1' if campaign == 'cpc_run1' else '4'})")

        ax.plot(rs, ideal, "-", color="0.3", label="ideal")
        ax.plot(rs, pc, ":", color="0.5", label="classical baseline")
        ax.set_xlabel("Grover iterations r")
        ax.set_xticks(rs)
        panel_label(ax, lab)
        ax.text(0.97, 0.95, f"n={n}, M={M}", transform=ax.transAxes, ha="right", va="top", fontsize=7)

    axes[0].set_ylabel("marked-state probability")
    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="outside upper center", ncol=4, fontsize=7.5, columnspacing=1.2)

    save_all(fig, "fig_m")


if __name__ == "__main__":
    main()
