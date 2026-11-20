"""Fig. D: TVD and Hellinger distance to three references, per (n, r) -- ideal (solid), the
generic FakeMarrakesh noisy simulator (dashed), and the calibration-day digital twin from Phase 1E
(dotted; qiskit-aer NoiseModel.from_backend_properties at the exact Oct-8 calibration snapshot).
Colour encodes problem size n; linestyle encodes the reference. One shared legend above both
panels. Reads results/cpc_revision/phase1d_distances.csv and phase1e_digital_twin.json; writes
figures/cpc/fig_d.{pdf,png}.

    python figures/cpc/scripts/fig_d.py
"""

import csv
import json
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))

TIER_LABEL = {"A": "n=3", "B": "n=4", "C": "n=5"}
TIER_COLOR = {"A": "#0072B2", "B": "#D55E00", "C": "#009E73"}
REF_STYLE = {"ideal": "-", "FakeMarrakesh": "--", "digital twin (Phase 1E)": ":"}


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1d_distances.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    twin = json.loads((ROOT / "results" / "cpc_revision" / "phase1e_digital_twin.json").read_text())
    twin_rows = {(r["tier"], r["r"]): r for r in twin["rows"]}

    fig, axes = plt.subplots(1, 2, figsize=(190 / 25.4, 58 / 25.4), sharex=True)
    for tier in ["A", "B", "C"]:
        color = TIER_COLOR[tier]
        trow = sorted([r for r in rows if r["tier"] == tier], key=lambda r: int(r["r"]))
        rs = [int(r["r"]) for r in trow]
        tvd_ideal = [float(r["tvd_hw_vs_ideal"]) for r in trow]
        tvd_sim = [float(r["tvd_hw_vs_noisy_sim"]) if r["tvd_hw_vs_noisy_sim"] else None for r in trow]
        tvd_twin = [twin_rows[(tier, r)]["tvd_hw_vs_digital_twin"] for r in rs]
        hel_ideal = [float(r["hellinger_hw_vs_ideal"]) for r in trow]
        hel_sim = [float(r["hellinger_hw_vs_noisy_sim"]) if r["hellinger_hw_vs_noisy_sim"] else None for r in trow]
        hel_twin = [twin_rows[(tier, r)]["hellinger_hw_vs_digital_twin"] for r in rs]

        axes[0].plot(rs, tvd_ideal, REF_STYLE["ideal"], color=color, marker="o")
        axes[0].plot(rs, tvd_sim, REF_STYLE["FakeMarrakesh"], color=color, marker="s")
        axes[0].plot(rs, tvd_twin, REF_STYLE["digital twin (Phase 1E)"], color=color, marker="^")
        axes[1].plot(rs, hel_ideal, REF_STYLE["ideal"], color=color, marker="o")
        axes[1].plot(rs, hel_sim, REF_STYLE["FakeMarrakesh"], color=color, marker="s")
        axes[1].plot(rs, hel_twin, REF_STYLE["digital twin (Phase 1E)"], color=color, marker="^")

    axes[0].set_ylabel("total variation distance")
    axes[1].set_ylabel("Hellinger distance")
    axes[0].set_title("(a)")
    axes[1].set_title("(b)")
    for ax in axes:
        ax.set_xlabel("Grover iterations r")

    size_handles = [mlines.Line2D([], [], color=TIER_COLOR[t], linestyle="-", marker="o", label=TIER_LABEL[t])
                    for t in ["A", "B", "C"]]
    ref_handles = [mlines.Line2D([], [], color="0.3", linestyle=ls, marker=m, label=lbl)
                   for lbl, ls, m in [("ideal", "-", "o"), ("FakeMarrakesh", "--", "s"),
                                       ("digital twin (Phase 1E)", ":", "^")]]
    fig.legend(handles=size_handles + ref_handles, loc="outside upper center", ncol=6, fontsize=6.5,
               columnspacing=1.0, handletextpad=0.5)

    fig.savefig(FIG / "fig_d.pdf")
    fig.savefig(FIG / "fig_d.png")
    print("wrote", FIG / "fig_d.pdf", "and .png")


if __name__ == "__main__":
    main()
