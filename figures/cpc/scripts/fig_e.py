"""Fig. E: diffusion pitfall -- matched vs Hadamard diffusion success probability vs r, 30 seeds
each, M=1 (n=3 ladder's M), box plot. Reads results/sim/start_state_design.json directly (per-seed
values are not duplicated into a CSV since the box plot needs the raw per-seed arrays).
Writes figures/cpc/fig_e.{pdf,png}.

    python figures/cpc/scripts/fig_e.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

M_SHOWN = 1


def main():
    data = json.loads((ROOT / "results" / "sim" / "start_state_design.json").read_text())
    by_r = {}
    for e in data["noiseless"]:
        if e["M"] != M_SHOWN or e["start"] not in ("ansatz_matched", "ansatz_hadamard"):
            continue
        by_r.setdefault(e["r"], {})[e["start"]] = e["values"]

    rs = sorted(by_r)
    matched_vals = [by_r[r]["ansatz_matched"] for r in rs]
    hadamard_vals = [by_r[r]["ansatz_hadamard"] for r in rs]

    fig, ax = plt.subplots(figsize=(90 / 25.4, 55 / 25.4))
    positions_m = [r - 0.17 for r in rs]
    positions_h = [r + 0.17 for r in rs]
    bp_m = ax.boxplot(matched_vals, positions=positions_m, widths=0.28, patch_artist=True,
                       showfliers=False)
    bp_h = ax.boxplot(hadamard_vals, positions=positions_h, widths=0.28, patch_artist=True,
                       showfliers=False)
    for box in bp_m["boxes"]:
        box.set_facecolor("#0072B2")
        box.set_alpha(0.6)
    for box in bp_h["boxes"]:
        box.set_facecolor("#D55E00")
        box.set_alpha(0.6)

    ax.set_xticks(rs)
    ax.set_xlabel("Grover iterations r")
    ax.set_ylabel(f"success probability (M={M_SHOWN}, 30 seeds)")
    ax.legend([bp_m["boxes"][0], bp_h["boxes"][0]], ["diffusion matched to start", "Hadamard diffusion (pitfall)"],
              loc="upper right")

    fig.savefig(FIG / "fig_e.pdf")
    fig.savefig(FIG / "fig_e.png")
    print("wrote", FIG / "fig_e.pdf", "and .png")


if __name__ == "__main__":
    main()
