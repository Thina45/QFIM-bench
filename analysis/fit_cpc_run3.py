"""Fit the global/per-size depolarizing model to Run 3 (cpc_run3, 3 repeats/tier), exactly as
analysis/phase1_cpc_revision.py's phase1b() does for the original campaigns and the earlier
Run 1/Run 4 fits -- reusing fit_fidelity_decay, ideal_probability and the same chi-square/reduced
chi-square bookkeeping, then adding the sqrt(reduced chi-square)-inflated CI
(analysis/inflate_fit_cis.py's convention). Needed for item 3 (effective-error ratio, 4 sessions)
of the CPC v4 pass. Read-only: only saved results/hardware/cpc_run3/*.json files are used.

    python analysis/fit_cpc_run3.py
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase1_cpc_revision import N_FIT_PARAMS, _residuals_and_chi_square, ideal_probability, marked_bitstrings  # noqa: E402

from qfim_bench.fit import fit_fidelity_decay  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "cpc_v4"
OUT.mkdir(parents=True, exist_ok=True)

TIERS = {
    "A": {"n": 3, "M": 1, "dir": ROOT / "results" / "hardware" / "cpc_run3", "files": [f"A_run{r}.json" for r in range(1, 4)]},
    "B": {"n": 4, "M": 2, "dir": ROOT / "results" / "hardware" / "cpc_run3", "files": [f"B_run{r}.json" for r in range(1, 4)]},
    "C": {"n": 5, "M": 4, "dir": ROOT / "results" / "hardware" / "cpc_run3", "files": [f"C_run{r}.json" for r in range(1, 4)]},
}
R_RANGE = range(0, 5)


def load_runs(tier):
    spec = TIERS[tier]
    return [json.loads((spec["dir"] / f).read_text(encoding="utf-8")) for f in spec["files"]]


def pooled_counts(tier, r):
    spec = TIERS[tier]
    n, M = spec["n"], spec["M"]
    cid = f"ladder_n{n}_M{M}_r{r}"
    runs = load_runs(tier)
    marked = marked_bitstrings(cid, n)
    tot_k, tot_n, gates = 0, 0, []
    for d in runs:
        c = d["counts"][cid]
        info = next(i for i, lbl in zip(d["job"]["circuits_info"], d["job"]["labels"]) if lbl == cid)
        gates.append(info["two_qubit_gates"])
        tot_k += sum(x for key, x in c.items() if key in marked)
        tot_n += sum(c.values())
    return tot_k, tot_n, float(np.mean(gates))


def inflate(ci, f, reduced_chi2):
    scale = math.sqrt(reduced_chi2) if reduced_chi2 and reduced_chi2 > 0 else 1.0
    return [f - (f - ci[0]) * scale, f + (ci[1] - f) * scale]


def main():
    per_size = {}
    all_g, all_ideal, all_k, all_n = [], [], [], []
    residual_rows = []
    for tier, spec in TIERS.items():
        n, M = spec["n"], spec["M"]
        N = 2**n
        g_list, ideal_list, k_list, n_list = [], [], [], []
        for r in R_RANGE:
            k, tot_n, gates = pooled_counts(tier, r)
            g_list.append(gates)
            ideal_list.append(ideal_probability(M, N, r))
            k_list.append(k)
            n_list.append(tot_n)
        fit = fit_fidelity_decay(g_list, ideal_list, k_list, n_list, n_bootstrap=300, seed=1)
        chi2, dof, reduced = _residuals_and_chi_square(
            g_list, ideal_list, k_list, n_list, fit.f, fit.p_noise, residual_rows, {"tier": tier, "r": None})
        for row, r in zip(residual_rows[-len(R_RANGE):], R_RANGE):
            row["r"] = r
        ci_inf = inflate(list(fit.f_ci), fit.f, reduced)
        per_size[tier] = {
            "n": n, "M": M, "N": N, "f": fit.f, "f_ci": list(fit.f_ci), "f_ci_inflated": ci_inf,
            "p_noise": fit.p_noise, "p_noise_ci": list(fit.p_noise_ci),
            "chi_square": chi2, "degrees_of_freedom": dof, "reduced_chi_square": reduced,
        }
        all_g.extend(g_list); all_ideal.extend(ideal_list); all_k.extend(k_list); all_n.extend(n_list)

    global_fit = fit_fidelity_decay(all_g, all_ideal, all_k, all_n, n_bootstrap=300, seed=1)
    global_chi2, global_dof, global_reduced = _residuals_and_chi_square(
        all_g, all_ideal, all_k, all_n, global_fit.f, global_fit.p_noise, [], {})
    global_ci_inf = inflate(list(global_fit.f_ci), global_fit.f, global_reduced)
    out = {
        "per_size": per_size,
        "global": {"f": global_fit.f, "f_ci": list(global_fit.f_ci), "f_ci_inflated": global_ci_inf,
                   "p_noise": global_fit.p_noise, "p_noise_ci": list(global_fit.p_noise_ci),
                   "chi_square": global_chi2, "degrees_of_freedom": global_dof,
                   "reduced_chi_square": global_reduced},
    }
    (OUT / "cpc_run3_fit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (OUT / "cpc_run3_fit_residuals.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(residual_rows[0].keys()))
        w.writeheader()
        w.writerows(residual_rows)
    print("global f:", global_fit.f, "inflated CI:", global_ci_inf, "reduced_chi2:", global_reduced)
    for t, d in per_size.items():
        print(t, "f:", d["f"], "inflated CI:", d["f_ci_inflated"], "reduced_chi2:", d["reduced_chi_square"])


if __name__ == "__main__":
    main()
