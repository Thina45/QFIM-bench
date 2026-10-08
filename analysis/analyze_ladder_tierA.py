"""Preregistered Tier A analysis (campaigns/ladder_v2/manifest.json, review/preregistration/).

Per circuit: mean over the 5 jobs with a 95% t-interval across them (4 d.f.), Wilson interval on the
pooled shots, comparison with the preregistered prediction band, and for ladder cells the TVD between
the pooled hardware counts and the pooled FakeMarrakesh counts with a permutation p-value against the
shot-noise floor. Then the four operating-point rules at r_opt on hardware, the offset of r=0 from
M/N, and the fidelity-decay fit against the simulator's value. The 5 jobs were run in one sitting
(deviation D1), so the t-interval does not include day-to-day drift.

    python analysis/analyze_ladder_tierA.py
"""

import json
import math
from pathlib import Path

import numpy as np

from qfim_bench.fit import fit_fidelity_decay
from qfim_bench.intervals import wilson_interval
from qfim_bench.tvd_calibration import counts_vector, two_sample_tvd_pvalue

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "results" / "hardware" / "ladder_v2"
T975_DF4 = 2.7764451051977987
SIM_F = 0.9967  # preregistered comparison value


def main() -> None:
    pred = {c["id"]: c for c in json.loads((ROOT / "review/preregistration/ladder_predictions.json").read_text())["circuits"]}
    sweep = json.loads((ROOT / "results/sim/feasibility_sweep.json").read_text())
    days = [json.loads((HW / f"day{d}.json").read_text()) for d in range(1, 6)]
    ids = sorted(pred_id for pred_id in pred if pred_id in days[0]["counts"])

    rows, g_by_id, pooled = [], {}, {}
    for cid in ids:
        n = int(cid.split("_")[1][1:])
        p = pred[cid]
        if cid.startswith("ladder"):
            keys = {format(i, f"0{n}b") for i in p["marked"]}
        else:
            keys = {("1" if cid.endswith("ones") else "0") * n}
        vals, tot_k, tot_n = [], 0, 0
        counts_sum: dict = {}
        for d in days:
            c = d["counts"][cid]
            k, tn = sum(x for key, x in c.items() if key in keys), sum(c.values())
            vals.append(k / tn); tot_k += k; tot_n += tn
            for key, x in c.items():
                counts_sum[key] = counts_sum.get(key, 0) + x
        mean, sd = float(np.mean(vals)), float(np.std(vals, ddof=1))
        half = T975_DF4 * sd / math.sqrt(5)
        lo_w, hi_w = wilson_interval(tot_k, tot_n)
        info = [next(i for i, l in zip(d["job"]["circuits_info"], d["job"]["labels"]) if l == cid) for d in days]
        g_by_id[cid] = float(np.mean([i["two_qubit_gates"] for i in info]))
        pooled[cid] = (counts_sum, tot_k, tot_n)
        row = {"id": cid, "daily": vals, "mean": mean, "sd": sd, "t_ci95": [mean - half, mean + half],
               "wilson_ci95_pooled": [lo_w, hi_w], "prediction": p["prediction"], "band": p["band_half_width"],
               "within_band": abs(mean - p["prediction"]) <= p["band_half_width"], "ideal": p["ideal"],
               "two_qubit_gates": g_by_id[cid], "layouts": sorted({tuple(i["physical_qubits"]) for i in info})}
        if cid.startswith("ladder"):
            sim = [x for x in sweep["points"] if x["style"] == "mcz" and x["n"] == p["n"] and x["M"] == p["M"] and x["r"] == p["r"]][0]
            sim_counts: dict = {}
            for cc in sim["noisy_counts"]:
                for key, x in cc.items():
                    sim_counts[key] = sim_counts.get(key, 0) + x
            res = two_sample_tvd_pvalue(counts_vector(counts_sum, n), counts_vector(sim_counts, n), draws=500, seed=1)
            row["tvd_hw_vs_sim"] = res["tvd"]; row["tvd_null_floor"] = res["null_floor"]; row["tvd_p_value"] = res["p_value"]
        rows.append(row)

    lad = {r["id"]: r for r in rows if r["id"].startswith("ladder")}
    n, M, r_opt = 3, 1, 2
    P = lad[f"ladder_n3_M1_r{r_opt}"]; P0 = lad["ladder_n3_M1_r0"]
    se_opt = P["sd"] / math.sqrt(5)
    p_max = max(r["mean"] for r in lad.values())
    rules = {"1_ratio_ge_3": P["mean"] >= 3 * P0["mean"], "2_floor_ge_0.40": P["mean"] >= 0.40,
             "3_gap_over_M/N_ge_0.20": (P["mean"] - M / 2**n) >= 0.20 and se_opt < 0.01,
             "4_is_max_within_sd": P["mean"] >= p_max - P["sd"]}
    offset_se = (P0["mean"] - M / 2**n) / (P0["sd"] / math.sqrt(5)) if P0["sd"] > 0 else float("nan")

    cells = sorted(lad.values(), key=lambda r: int(r["id"].rsplit("_r", 1)[1]))
    g = [r["two_qubit_gates"] for r in cells]
    ideal = [r["ideal"] for r in cells]
    k = [pooled[r["id"]][1] for r in cells]
    nn = [pooled[r["id"]][2] for r in cells]
    fit = fit_fidelity_decay(g, ideal, k, nn, n_bootstrap=300, seed=1)

    out = {"rows": rows, "criterion_rules_hardware": rules, "criterion_pass": all(rules.values()),
           "P_r_opt": P["mean"], "P_r0": P0["mean"], "ratio": P["mean"] / P0["mean"],
           "r0_offset_from_M_over_N_in_SE": offset_se,
           "fit": {"f_per_2q_hw": fit.f, "f_ci95": fit.f_ci, "p_noise": fit.p_noise, "p_noise_ci95": fit.p_noise_ci,
                   "simulator_f": SIM_F},
           "billed_seconds": [d["job"]["usage_seconds"] for d in days]}
    (HW / "analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    for r in rows:
        extra = f"  TVD vs sim {r['tvd_hw_vs_sim']:.3f} (floor {r['tvd_null_floor']:.3f}, p={r['tvd_p_value']:.3f})" if "tvd_p_value" in r else ""
        print(f"{r['id']:20s} {r['mean']:.3f} t-CI [{r['t_ci95'][0]:.3f},{r['t_ci95'][1]:.3f}] pred {r['prediction']:.3f}+/-{r['band']:.3f} "
              f"{'IN ' if r['within_band'] else 'OUT'} ideal {r['ideal']:.3f}{extra}")
    print("rules on hardware:", rules, "-> PASS" if out["criterion_pass"] else "-> fail")
    print(f"P(r_opt)/P(r=0) = {out['ratio']:.2f};  r=0 offset from M/N = {offset_se:.2f} SE")
    print(f"fit: f_hw={fit.f:.5f} CI [{fit.f_ci[0]:.5f},{fit.f_ci[1]:.5f}] vs simulator {SIM_F}; p_noise {fit.p_noise:.3f}")
    print("billed per job:", out["billed_seconds"], "-> total with probe", sum(out["billed_seconds"]) + 4.0)


if __name__ == "__main__":
    main()
