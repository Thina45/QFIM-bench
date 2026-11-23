"""Fig. S1 (supplementary): depolarizing-fit residuals (measured - fitted) vs r, per size, Oct 8,
for BOTH noise models compared in results/cpc_v4/REPORT.md item 4 -- Model 1 (solid: f and p_noise
both free, the original fit) and Model 2 (dashed: f free, p_noise fixed at the theoretical floor
M/N, ideal curve scaled by a SPAM factor estimated from readout controls). Reduced chi-square per
size and model is reported in captions.md, not the image.
Reads results/cpc_revision/phase1b_residuals.csv, phase1b_global_fit.json, and
results/cpc_v4/two_param_spam_fit.json (Model 2, added this pass).

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

sys.path.insert(0, str(ROOT / "analysis"))
from phase1_cpc_revision import ideal_probability  # noqa: E402
from qfim_bench.fit import decay_model  # noqa: E402

TIER_LABEL = {"A": "n=3", "B": "n=4", "C": "n=5"}
TIER_NM = {"A": (3, 1), "B": (4, 2), "C": (5, 4)}


def main():
    with (ROOT / "results" / "cpc_revision" / "phase1b_residuals.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    spam = json.loads((ROOT / "results" / "cpc_v4" / "two_param_spam_fit.json").read_text())["Oct8"]["per_size"]

    fig, ax = plt.subplots(figsize=mm2in(90, 68))
    for tier in ["A", "B", "C"]:
        trow = sorted([r for r in rows if r["tier"] == tier], key=lambda r: int(r["r"]))
        rs = [int(r["r"]) for r in trow]
        res1 = [float(r["residual"]) for r in trow]
        ax.plot(rs, res1, "o-", color=TIER_COLOR[tier], label=f"{TIER_LABEL[tier]} (Model 1)")

        n, M = TIER_NM[tier]
        N = 2**n
        f2 = spam[tier]["model2_f_spam"]["f"]
        R = spam[tier]["R_spam"]
        res2 = []
        for r, row in zip(rs, trow):
            ideal = ideal_probability(M, N, r) * R
            g = float(row["two_qubit_gates"])
            p2 = float(decay_model([g], [ideal], f2, M / N)[0])
            res2.append(float(row["hw_mean"]) - p2)
        ax.plot(rs, res2, "^--", color=TIER_COLOR[tier], alpha=0.6,
                label=f"{TIER_LABEL[tier]} (Model 2)")

    ax.axhline(0.0, color="0.4", linewidth=0.8, linestyle="--")
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_xlabel("Grover iterations r")
    ax.set_ylabel("residual (measured $-$ fitted)")
    ax.legend(loc="best", fontsize=5.5, ncol=2)

    save_all(fig, "fig_s1")


if __name__ == "__main__":
    main()
