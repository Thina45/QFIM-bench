"""Fig. D: TVD and Hellinger distance to ideal and to the FakeMarrakesh noisy simulator, per (n, r).
Reads results/cpc_revision/phase1d_distances.csv; writes figures/cpc/fig_d.{pdf,png}.

    python figures/cpc/scripts/fig_d.py
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

TIER_LABEL = {"A": "n=3", "B": "n=4", "C": "n=5"}


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1d_distances.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fig, axes = plt.subplots(1, 2, figsize=(190 / 25.4, 55 / 25.4), sharex=True)
    for tier in ["A", "B", "C"]:
        trow = sorted([r for r in rows if r["tier"] == tier], key=lambda r: int(r["r"]))
        rs = [int(r["r"]) for r in trow]
        tvd_ideal = [float(r["tvd_hw_vs_ideal"]) for r in trow]
        tvd_sim = [float(r["tvd_hw_vs_noisy_sim"]) if r["tvd_hw_vs_noisy_sim"] else None for r in trow]
        hel_ideal = [float(r["hellinger_hw_vs_ideal"]) for r in trow]
        hel_sim = [float(r["hellinger_hw_vs_noisy_sim"]) if r["hellinger_hw_vs_noisy_sim"] else None for r in trow]

        axes[0].plot(rs, tvd_ideal, "o-", label=f"{TIER_LABEL[tier]} vs ideal")
        axes[0].plot(rs, tvd_sim, "s--", label=f"{TIER_LABEL[tier]} vs FakeMarrakesh")
        axes[1].plot(rs, hel_ideal, "o-", label=f"{TIER_LABEL[tier]} vs ideal")
        axes[1].plot(rs, hel_sim, "s--", label=f"{TIER_LABEL[tier]} vs FakeMarrakesh")

    axes[0].set_ylabel("total variation distance")
    axes[1].set_ylabel("Hellinger distance")
    for ax in axes:
        ax.set_xlabel("Grover iterations r")
    axes[0].legend(loc="upper left", fontsize=6.5, ncol=1)

    fig.savefig(FIG / "fig_d.pdf")
    fig.savefig(FIG / "fig_d.png")
    print("wrote", FIG / "fig_d.pdf", "and .png")


if __name__ == "__main__":
    main()
