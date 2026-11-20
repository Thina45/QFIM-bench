"""Fig. F: day-to-day drift at r=2 -- the H1 cell definition, plotted consistently for all three
sizes (previously n=4/5 used their own r_opt=1, which mixed iteration counts with the H1 cell and
the drift table; now all three panels use r=2) -- comparing the 2026-10-08 sitting (ladder_v2/v2b),
Run 1 and Run 3 (both ibm_marrakesh, same-day-type replication, Run 3 >=12h after Run 1). Error
bars are 95% t-CIs (4 d.f. for 5-repeat sittings, 2 d.f. for Run 3's 3 repeats). n=3 is marked with
a hollow marker: its two-qubit gate count differs between Run 1 (39) and Run 3 (45) (see REPORT.md
section 13/H1 confound), so that point is gate-count-confounded, unlike n=4 and n=5 (both
gate-matched, 113=113 and 1354->1355 respectively).
Reads results/hardware/ladder_v2/analysis.json, results/hardware/ladder_v2b/analysis.json,
results/cpc_revision/cpc_runs_analysis.json.

    python figures/cpc/scripts/fig_f.py
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in  # noqa: E402

R_OPT = {3: ("ladder_n3_M1_r2", "A"), 4: ("ladder_n4_M2_r2", "B"), 5: ("ladder_n5_M4_r2", "C")}
GATE_CONFOUNDED_N = {3}  # n=3's r=2 circuit has a different two-qubit gate count Run1 vs Run3


def oct8_rows():
    a = json.load(open(ROOT / "results/hardware/ladder_v2/analysis.json"))["rows"]
    bc = json.load(open(ROOT / "results/hardware/ladder_v2b/analysis.json"))
    return {r["id"]: r for r in a + bc["B"]["rows"] + bc["C"]["rows"]}


def main():
    oct8 = oct8_rows()
    new = json.load(open(ROOT / "results/cpc_revision/cpc_runs_analysis.json"))

    fig, ax = plt.subplots(figsize=mm2in(90, 70))
    xs = [0, 1, 2]
    sittings = ["2026-10-08", "2026-11-19 (Run 1)", "2026-11-20 (Run 3)"]
    colors = {"2026-10-08": "#0072B2", "2026-11-19 (Run 1)": "#D55E00",
              "2026-11-20 (Run 3)": "#009E73"}
    campaign_for = {"2026-11-19 (Run 1)": "cpc_run1", "2026-11-20 (Run 3)": "cpc_run3"}
    offsets = {s: (i - 1) * 0.12 for i, s in enumerate(sittings)}
    for sitting in sittings:
        means, los, his, hollow = [], [], [], []
        for n, (cid, tier) in R_OPT.items():
            if sitting == "2026-10-08":
                r = oct8[cid]
            else:
                r = new[campaign_for[sitting]][tier][cid]
            means.append(r["mean"])
            los.append(r["mean"] - r["t_ci95"][0])
            his.append(r["t_ci95"][1] - r["mean"])
            hollow.append(n in GATE_CONFOUNDED_N)
        x_pos = [x + offsets[sitting] for x in xs]
        ax.errorbar(x_pos, means, yerr=[los, his], fmt="none", color=colors[sitting],
                     capsize=2, zorder=1)
        for x, m, h in zip(x_pos, means, hollow):
            ax.scatter([x], [m], marker="o", s=22,
                       facecolor="none" if h else colors[sitting],
                       edgecolor=colors[sitting], linewidth=1.2, zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(["n=3", "n=4", "n=5"])
    ax.set_xlim(-0.4, 2.4)
    ax.set_ylabel("Success probability (r=2)")

    import matplotlib.lines as mlines
    date_handles = [mlines.Line2D([], [], marker="o", linestyle="none", color=colors[s], label=s)
                    for s in sittings]
    hollow_handle = mlines.Line2D([], [], marker="o", linestyle="none", markerfacecolor="none",
                                   markeredgecolor="0.3", label="hollow marker = two-qubit gate "
                                   "count differs (Run 1: 39, Run 3: 45)")
    fig.legend(handles=date_handles + [hollow_handle], loc="outside upper center", ncol=2,
               fontsize=6, frameon=False)
    save_all(fig, "fig_f")


if __name__ == "__main__":
    main()
