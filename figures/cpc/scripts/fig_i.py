"""Fig. I: fitted global depolarizing f vs. median two-qubit gate error, one point per
device/session (2026-10-08 ibm_marrakesh original campaign, 2026-11-19 Run 1 ibm_marrakesh,
2026-11-19 Run 4 ibm_kingston). The median 2Q error is computed from the exact calibration
snapshot at that session's recorded calibration_timestamp(s), restricted to the physical qubit
pairs actually used by that session's ladder circuits -- not a generic device-wide median, so all
three points are comparable on the same basis.

Reads results/cpc_revision/phase1b_global_fit.json, run1_fit.json, run4_fit.json, and
run1_run4_median_2q_error.json, plus results/cpc_revision/historical_calibration.json for the
2026-10-08 point. Writes figures/cpc/fig_i.{pdf,png}.

    python figures/cpc/scripts/fig_i.py
"""
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
CPC = ROOT / "results" / "cpc_revision"
plt.style.use(str(FIG / "cpc.mplstyle"))


def main():
    oct8_json = json.loads((CPC / "phase1b_global_fit.json").read_text())["global"]
    hist = json.loads((CPC / "historical_calibration.json").read_text())
    oct8_errs = [g["error"] for k in ["tierA_n3", "tierB_n4", "tierC_run1-3_n5"] for g in hist[k]["two_qubit_gate_errors"]]
    oct8_err = float(np.median(oct8_errs))

    run1_fit = json.loads((CPC / "cpc_run1_fit.json").read_text())["global"]
    run4_fit = json.loads((CPC / "cpc_run4_fit.json").read_text())["global"]
    med_err = json.loads((CPC / "run1_run4_median_2q_error.json").read_text())
    run1_err = med_err["run1_by_calibration"]["2026-11-19 14:35:58+05:30"][1]
    run4_err = med_err["run4"][1]

    def inflated_ci(fit):
        return fit.get("f_ci95_inflated") or fit.get("f_ci_inflated") or fit.get("f_ci95") or fit["f_ci"]

    points = [
        ("ibm_marrakesh, 2026-10-08", oct8_err, oct8_json["f"], inflated_ci(oct8_json)),
        ("ibm_marrakesh, Run 1 (2026-11-19)", run1_err, run1_fit["f"], inflated_ci(run1_fit)),
        ("ibm_kingston, Run 4 (2026-11-19)", run4_err, run4_fit["f"], inflated_ci(run4_fit)),
    ]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(160 / 25.4, 60 / 25.4))
    colors = ["#0072B2", "#D55E00", "#009E73"]
    for (label, err, f, f_ci), c in zip(points, colors):
        yerr = [[f - f_ci[0]], [f_ci[1] - f]]
        ax.errorbar([err * 1e3], [f], yerr=yerr, fmt="o", color=c, label=label, capsize=3)

    ax.set_xlabel("median two-qubit gate error ($\\times 10^{-3}$), used-qubit pairs only")
    ax.set_ylabel("fitted global depolarizing $f$")
    ax.legend(fontsize=6, loc="lower left")
    ax.set_title("(a) fit vs. calibrated error", fontsize=8)

    ratios = []
    for (label, err, f, f_ci), c in zip(points, colors):
        r = (1 - f) / err
        r_lo, r_hi = (1 - f_ci[1]) / err, (1 - f_ci[0]) / err
        ratios.append((label, r, r_lo, r_hi, c))
        ax2.errorbar([label], [r], yerr=[[r - r_lo], [r_hi - r]], fmt="o", color=c, capsize=3)
    ax2.set_ylabel("effective error ratio $(1-f)\\,/\\,$median two-qubit error")
    ax2.set_xticks(range(len(points)))
    ax2.set_xticklabels([p[0] for p in points], rotation=20, ha="right", fontsize=6)
    ax2.set_title("(b) effective vs. calibrated error ratio (n=3 points; observation, not a law)", fontsize=8)

    fig.tight_layout()
    fig.subplots_adjust(wspace=0.45, top=0.85)
    fig.savefig(FIG / "fig_i.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_i.png", dpi=300, bbox_inches="tight")
    print("saved fig_i.{pdf,png}")
    for label, err, f, f_ci in points:
        print(f"{label}: 2Q_err={err:.5f} f={f:.5f} inflated_CI={f_ci}")
    for label, r, r_lo, r_hi, _ in ratios:
        print(f"{label}: ratio={r:.3f} CI=[{r_lo:.3f},{r_hi:.3f}]")


if __name__ == "__main__":
    main()
