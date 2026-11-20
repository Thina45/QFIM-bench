"""Fig. G: dynamical decoupling on (Run 1 Tier B) vs off (Run 2) at n=4, vs r. Error bars are
95% t-CIs (4 d.f., 5 repeats). Reads results/cpc_revision/cpc_runs_analysis.json.

    python figures/cpc/scripts/fig_g.py
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


def main():
    new = json.load(open(ROOT / "results/cpc_revision/cpc_runs_analysis.json"))
    on = new["cpc_run1"]["B"]
    off = new["cpc_run2"]["B"]

    fig, ax = plt.subplots(figsize=mm2in(90, 65))
    rs = list(range(5))
    for label, data, color, dx in [("DD on (Run 1)", on, "#0072B2", -0.07), ("DD off (Run 2)", off, "#D55E00", 0.07)]:
        means, los, his = [], [], []
        for r in rs:
            cell = data[f"ladder_n4_M2_r{r}"]
            means.append(cell["mean"])
            los.append(cell["mean"] - cell["t_ci95"][0])
            his.append(cell["t_ci95"][1] - cell["mean"])
        ax.errorbar([x + dx for x in rs], means, yerr=[los, his], fmt="o", label=label,
                    color=color, capsize=2, markersize=4)
    ax.set_xticks(rs)
    ax.set_xlabel("Grover iterations r")
    ax.set_ylabel("Success probability (n=4)")
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=2, fontsize=7.5, frameon=False)
    save_all(fig, "fig_g")


if __name__ == "__main__":
    main()
