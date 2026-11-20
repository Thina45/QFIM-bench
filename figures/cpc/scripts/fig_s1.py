"""Fig. S1 (supplementary): depolarizing-fit residuals (measured - fitted) vs r, per size, Oct 8.
Reduced chi-square per size is reported in captions.md, not the image.
Reads results/cpc_revision/phase1b_residuals.csv and phase1b_global_fit.json.

    python figures/cpc/scripts/fig_s1.py
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
from style_constants import TIER_COLOR, mm2in  # noqa: E402

TIER_LABEL = {"A": "n=3", "B": "n=4", "C": "n=5"}


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1b_residuals.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fig, ax = plt.subplots(figsize=mm2in(90, 65))
    for tier in ["A", "B", "C"]:
        trow = sorted([r for r in rows if r["tier"] == tier], key=lambda r: int(r["r"]))
        rs = [int(r["r"]) for r in trow]
        res = [float(r["residual"]) for r in trow]
        ax.plot(rs, res, "o-", color=TIER_COLOR[tier], label=TIER_LABEL[tier])
    ax.axhline(0.0, color="0.4", linewidth=0.8, linestyle="--")
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_xlabel("Grover iterations r")
    ax.set_ylabel("residual (measured $-$ fitted)")
    ax.legend(loc="best")

    save_all(fig, "fig_s1")


if __name__ == "__main__":
    main()
