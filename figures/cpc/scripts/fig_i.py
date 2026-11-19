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
    oct8_fit = json.loads((CPC / "phase1b_global_fit.json").read_text())["global"]["f"]
    oct8_fit_ci = json.loads((CPC / "phase1b_global_fit.json").read_text())["global"]["f_ci95"]
    hist = json.loads((CPC / "historical_calibration.json").read_text())
    oct8_errs = [g["error"] for k in ["tierA_n3", "tierB_n4", "tierC_run1-3_n5"] for g in hist[k]["two_qubit_gate_errors"]]
    oct8_err = float(np.median(oct8_errs))

    run1_fit = json.loads((CPC / "cpc_run1_fit.json").read_text())["global"]
    run4_fit = json.loads((CPC / "cpc_run4_fit.json").read_text())["global"]
    med_err = json.loads((CPC / "run1_run4_median_2q_error.json").read_text())
    run1_err = med_err["run1_by_calibration"]["2026-11-19 14:35:58+05:30"][1]
    run4_err = med_err["run4"][1]

    points = [
        ("ibm_marrakesh, 2026-10-08", oct8_err, oct8_fit, oct8_fit_ci),
        ("ibm_marrakesh, Run 1 (2026-11-19)", run1_err, run1_fit["f"], run1_fit["f_ci"]),
        ("ibm_kingston, Run 4 (2026-11-19)", run4_err, run4_fit["f"], run4_fit["f_ci"]),
    ]

    fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
    colors = ["#0072B2", "#D55E00", "#009E73"]
    for (label, err, f, f_ci), c in zip(points, colors):
        yerr = [[f - f_ci[0]], [f_ci[1] - f]]
        ax.errorbar([err * 1e3], [f], yerr=yerr, fmt="o", color=c, label=label, capsize=3)

    ax.set_xlabel("median two-qubit gate error ($\\times 10^{-3}$), used-qubit pairs only")
    ax.set_ylabel("fitted global depolarizing $f$")
    ax.legend(fontsize=6, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "fig_i.pdf")
    fig.savefig(FIG / "fig_i.png", dpi=300)
    print("saved fig_i.{pdf,png}")
    for label, err, f, f_ci in points:
        print(f"{label}: 2Q_err={err:.5f} f={f:.5f} CI={f_ci}")


if __name__ == "__main__":
    main()
