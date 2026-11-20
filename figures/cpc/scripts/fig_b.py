"""Fig. B: hardware minus classical baseline per (n, r), with 95% CI, zero line.
Reads results/cpc_revision/phase1a_classical_baseline.csv; writes figures/cpc/fig_b.{pdf,png}.

    python figures/cpc/scripts/fig_b.py
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in  # noqa: E402

TIER_LABEL = {"A": "n=3", "B": "n=4", "C": "n=5"}


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1a_classical_baseline.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fig, ax = plt.subplots(figsize=mm2in(90, 58))
    width = 0.25
    offsets = {"A": -width, "B": 0.0, "C": width}
    for tier in ["A", "B", "C"]:
        trow = sorted([r for r in rows if r["tier"] == tier], key=lambda r: int(r["r"]))
        rs = np.array([int(r["r"]) for r in trow])
        diff = np.array([float(r["hw_mean"]) - float(r["classical_Pc"]) for r in trow])
        lo = np.array([float(r["hw_mean"]) - float(r["hw_t_ci95_lo"]) for r in trow])
        hi = np.array([float(r["hw_t_ci95_hi"]) - float(r["hw_mean"]) for r in trow])
        ax.errorbar(rs + offsets[tier], diff, yerr=[lo, hi], fmt="o", label=TIER_LABEL[tier])
    ax.axhline(0.0, color="0.4", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Grover iterations r")
    ax.set_ylabel("hardware mean - classical $P_c(r)$")
    ax.set_xticks(sorted({int(r["r"]) for r in rows}))
    ax.legend(loc="best")

    save_all(fig, "fig_b")


if __name__ == "__main__":
    main()
