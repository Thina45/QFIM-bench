"""Figure: preregistered ladder campaign, ideal vs hardware success probability (n=3, 4, 5).

Reads results/hardware/ladder_v2/analysis.json and ladder_v2b/analysis.json. Hardware points are the
mean of 5 jobs with the 95% t-interval across those jobs (one sitting, one calibration window, so no
drift). Writes a PNG (300 dpi) to figures/.

    python analysis/make_ladder_figure.py            # as in the paper figure
    python analysis/make_ladder_figure.py --prediction   # also draw the simulator prediction and its band
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
HW = ROOT / "results" / "hardware"
PANELS = [(3, 1, "A"), (4, 2, "B"), (5, 4, "C")]
BLUE, BLACK, ORANGE = "#1f77b4", "#222222", "#d55e00"


def ladder_rows():
    a = json.loads((HW / "ladder_v2" / "analysis.json").read_text(encoding="utf-8"))
    b = json.loads((HW / "ladder_v2b" / "analysis.json").read_text(encoding="utf-8"))
    return {3: a["rows"], 4: b["B"]["rows"], 5: b["C"]["rows"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prediction", action="store_true")
    args = ap.parse_args()

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.linewidth": 0.8})
    rows = ladder_rows()
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.9), sharey=True, constrained_layout=True)

    for ax, (n, M, _) in zip(axes, PANELS):
        lad = sorted((r for r in rows[n] if r["id"].startswith("ladder")), key=lambda r: int(r["id"].rsplit("_r", 1)[1]))
        r_vals = list(range(len(lad)))
        ideal = [r["ideal"] for r in lad]
        mean = [r["mean"] for r in lad]
        err_lo = [r["mean"] - r["t_ci95"][0] for r in lad]
        err_hi = [r["t_ci95"][1] - r["mean"] for r in lad]

        ax.axhline(M / 2**n, color="0.55", ls=(0, (1, 2)), lw=1.1, zorder=1)
        if args.prediction:
            pred = [r["prediction"] for r in lad]
            band = [r["band"] for r in lad]
            ax.fill_between(r_vals, [p - b for p, b in zip(pred, band)], [p + b for p, b in zip(pred, band)],
                            color=ORANGE, alpha=0.15, lw=0, zorder=1)
            ax.plot(r_vals, pred, color=ORANGE, lw=1.4, marker="^", ms=4.5, zorder=2)
        ax.plot(r_vals, ideal, color=BLACK, lw=1.4, ls=(0, (4, 2)), marker="o", ms=4.5, zorder=3)
        ax.errorbar(r_vals, mean, yerr=[err_lo, err_hi], color=BLUE, lw=1.8, marker="s", ms=5.5,
                    capsize=3, capthick=1.2, elinewidth=1.2, zorder=4)

        ax.set_title(f"n={n}, M={M}  (M/N=1/8)", fontsize=11, pad=8)
        ax.set_xlabel("Grover iterations r")
        ax.set_xticks(r_vals)
        ax.set_ylim(0, 1.02)
        ax.grid(axis="y", color="0.9", lw=0.7, zorder=0)
        ax.text(0.97, 0.97, f"{round(lad[2]['two_qubit_gates'])} two-qubit\ngates at r=2", transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5, color="0.35", linespacing=1.3)
    axes[0].set_ylabel("Success probability")

    handles = [
        plt.Line2D([], [], color=BLACK, lw=1.4, ls=(0, (4, 2)), marker="o", ms=4.5, label="Ideal (noiseless)"),
        plt.Line2D([], [], color=BLUE, lw=1.8, marker="s", ms=5.5, label="ibm_marrakesh (mean of 5 jobs, 95% CI)"),
        plt.Line2D([], [], color="0.55", ls=(0, (1, 2)), lw=1.1, label="M/N (no amplification)"),
    ]
    if args.prediction:
        handles.insert(1, plt.Line2D([], [], color=ORANGE, lw=1.4, marker="^", ms=4.5, label="FakeMarrakesh prediction ± band"))
    fig.legend(handles=handles, loc="outside lower center", ncol=len(handles), frameon=False, fontsize=9.5)
    fig.suptitle("Preregistered ladder campaign: ideal vs. hardware success probability", fontsize=12.5, fontweight="bold")

    OUT.mkdir(exist_ok=True)
    stem = "ladder_ideal_vs_hardware" + ("_with_prediction" if args.prediction else "")
    fig.savefig(OUT / f"{stem}.png", dpi=300)
    print("saved", OUT / f"{stem}.png")


if __name__ == "__main__":
    main()
