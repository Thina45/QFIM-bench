"""Fig. F: day-to-day drift at r=2 (the operating point) per n, comparing the 2026-10-08 sitting
(ladder_v2/v2b) against Run 1 (ibm_marrakesh, same-day-type replication). Error bars are 95% t-CIs
(4 d.f., 5 repeats per sitting). Reads results/hardware/ladder_v2/analysis.json,
results/hardware/ladder_v2b/analysis.json, results/cpc_revision/cpc_runs_analysis.json.

    python figures/cpc/scripts/fig_f.py
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

R_OPT = {3: ("ladder_n3_M1_r2", "A"), 4: ("ladder_n4_M2_r1", "B"), 5: ("ladder_n5_M4_r1", "C")}


def oct8_rows():
    a = json.load(open(ROOT / "results/hardware/ladder_v2/analysis.json"))["rows"]
    bc = json.load(open(ROOT / "results/hardware/ladder_v2b/analysis.json"))
    return {r["id"]: r for r in a + bc["B"]["rows"] + bc["C"]["rows"]}


def main():
    oct8 = oct8_rows()
    new = json.load(open(ROOT / "results/cpc_revision/cpc_runs_analysis.json"))

    fig, ax = plt.subplots(figsize=(90 / 25.4, 65 / 25.4))
    xs = [0, 1, 2]
    sittings = ["2026-10-08", "Run 1 (same session type)"]
    colors = {"2026-10-08": "#0072B2", "Run 1 (same session type)": "#D55E00"}
    for j, sitting in enumerate(sittings):
        means, los, his = [], [], []
        for n, (cid, tier) in R_OPT.items():
            if sitting == "2026-10-08":
                r = oct8[cid]
            else:
                r = new["cpc_run1"][tier][cid]
            means.append(r["mean"])
            los.append(r["mean"] - r["t_ci95"][0])
            his.append(r["t_ci95"][1] - r["mean"])
        ax.errorbar([x + (j - 0.5) * 0.12 for x in xs], means, yerr=[los, his], fmt="o",
                    label=sitting, color=colors[sitting], capsize=2, markersize=4)
    ax.set_xticks(xs)
    ax.set_xticklabels(["n=3 (r=2)", "n=4 (r=1)", "n=5 (r=1)"])
    ax.set_ylabel("Success probability")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG / "fig_f.pdf")
    fig.savefig(FIG / "fig_f.png", dpi=300)
    print("wrote", FIG / "fig_f.pdf", "and .png")


if __name__ == "__main__":
    main()
