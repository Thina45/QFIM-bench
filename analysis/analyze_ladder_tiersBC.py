"""Preregistered analysis for Tiers B (n=4, M=2) and C (n=5, M=4); same procedure as Tier A.

Per circuit: mean over the 5 runs, 95% t-interval across runs (4 d.f.), band check against the
preregistered prediction, TVD to the pooled FakeMarrakesh counts (permutation p-value). Per tier: the
four operating-point rules at r_opt=2, the r=0 offset from M/N, a fidelity-decay fit. Cross-tier: the
echo ordering (H4) including Tier A. The runs shared one sitting (D1), so the t-intervals exclude drift.

    python analysis/analyze_ladder_tiersBC.py
"""

import json
import math
from pathlib import Path

import numpy as np

from qfim_bench.fit import fit_fidelity_decay
from qfim_bench.intervals import wilson_interval
from qfim_bench.tvd_calibration import counts_vector, two_sample_tvd_pvalue

ROOT = Path(__file__).resolve().parents[1]
HWB = ROOT / "results" / "hardware" / "ladder_v2b"
T975 = 2.7764451051977987
TIERS = {"B": (4, 2), "C": (5, 4)}
R_OPT = 2


def analyse_tier(tier, n, M, pred, sweep):
    runs = [json.loads((HWB / f"{tier}_run{r}.json").read_text()) for r in range(1, 6)]
    rows, pooled = [], {}
    for cid in sorted(c for c in pred if c.split("_")[1] == f"n{n}"):
        p = pred[cid]
        keys = ({format(i, f"0{n}b") for i in p["marked"]} if cid.startswith("ladder")
                else {("1" if cid.endswith("ones") else "0") * n})
        vals, tk, tn, csum = [], 0, 0, {}
        for d in runs:
            c = d["counts"][cid]
            k, t = sum(x for key, x in c.items() if key in keys), sum(c.values())
            vals.append(k / t); tk += k; tn += t
            for key, x in c.items():
                csum[key] = csum.get(key, 0) + x
        mean, sd = float(np.mean(vals)), float(np.std(vals, ddof=1))
        half = T975 * sd / math.sqrt(5)
        info = [next(i for i, l in zip(d["job"]["circuits_info"], d["job"]["labels"]) if l == cid) for d in runs]
        row = {"id": cid, "daily": vals, "mean": mean, "sd": sd, "t_ci95": [mean - half, mean + half],
               "wilson_ci95_pooled": list(wilson_interval(tk, tn)), "prediction": p["prediction"], "band": p["band_half_width"],
               "within_band": abs(mean - p["prediction"]) <= p["band_half_width"], "ideal": p["ideal"],
               "two_qubit_gates": float(np.mean([i["two_qubit_gates"] for i in info])),
               "layouts": sorted({tuple(i["physical_qubits"]) for i in info})}
        pooled[cid] = (csum, tk, tn)
        if cid.startswith("ladder"):
            sim = [x for x in sweep["points"] if x["style"] == "mcz" and x["n"] == n and x["M"] == M and x["r"] == p["r"]][0]
            sc = {}
            for cc in sim["noisy_counts"]:
                for key, x in cc.items():
                    sc[key] = sc.get(key, 0) + x
            res = two_sample_tvd_pvalue(counts_vector(csum, n), counts_vector(sc, n), draws=500, seed=1)
            row.update(tvd_hw_vs_sim=res["tvd"], tvd_null_floor=res["null_floor"], tvd_p_value=res["p_value"])
        rows.append(row)

    lad = sorted((r for r in rows if r["id"].startswith("ladder")), key=lambda r: int(r["id"].rsplit("_r", 1)[1]))
    P, P0 = lad[R_OPT], lad[0]
    se = P["sd"] / math.sqrt(5)
    p_max = max(r["mean"] for r in lad)
    rules = {"1_ratio_ge_3": P["mean"] >= 3 * P0["mean"], "2_floor_ge_0.40": P["mean"] >= 0.40,
             "3_gap_over_M/N_ge_0.20": (P["mean"] - M / 2**n) >= 0.20 and se < 0.01,
             "4_is_max_within_sd": P["mean"] >= p_max - P["sd"]}
    fit = fit_fidelity_decay([r["two_qubit_gates"] for r in lad], [r["ideal"] for r in lad],
                             [pooled[r["id"]][1] for r in lad], [pooled[r["id"]][2] for r in lad], n_bootstrap=300, seed=1)
    return {"rows": rows, "rules": rules, "pass": all(rules.values()), "P_r_opt": P["mean"], "P_r0": P0["mean"],
            "ratio": P["mean"] / P0["mean"], "peak_r": int(max(lad, key=lambda r: r["mean"])["id"].rsplit("_r", 1)[1]),
            "fit": {"f": fit.f, "f_ci95": fit.f_ci, "p_noise": fit.p_noise, "p_noise_ci95": fit.p_noise_ci},
            "billed": [d["job"]["usage_seconds"] for d in runs]}


def main() -> None:
    pred = {c["id"]: c for c in json.loads((ROOT / "review/preregistration/ladder_predictions.json").read_text())["circuits"]}
    sweep = json.loads((ROOT / "results/sim/feasibility_sweep.json").read_text())
    out = {t: analyse_tier(t, n, M, pred, sweep) for t, (n, M) in TIERS.items()}
    a = json.loads((ROOT / "results/hardware/ladder_v2/analysis.json").read_text())
    echo = {"A": next(r["mean"] for r in a["rows"] if r["id"].startswith("echo"))}
    for t in TIERS:
        echo[t] = next(r["mean"] for r in out[t]["rows"] if r["id"].startswith("echo"))
    out["echo_by_tier"] = echo
    out["H4_echo_ordering_A_gt_B_gt_C"] = echo["A"] > echo["B"] > echo["C"]
    (HWB / "analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    for t in TIERS:
        print(f"--- Tier {t} (n={TIERS[t][0]}, M={TIERS[t][1]}) ---")
        for r in out[t]["rows"]:
            ex = f"  TVD vs sim {r['tvd_hw_vs_sim']:.3f} (floor {r['tvd_null_floor']:.3f}, p={r['tvd_p_value']:.3f})" if "tvd_p_value" in r else ""
            print(f"{r['id']:20s} {r['mean']:.3f} [{r['t_ci95'][0]:.3f},{r['t_ci95'][1]:.3f}] pred {r['prediction']:.3f}+/-{r['band']:.3f} "
                  f"{'IN ' if r['within_band'] else 'OUT'} ideal {r['ideal']:.3f} 2Q {r['two_qubit_gates']:.0f}{ex}")
        o = out[t]
        print("rules:", o["rules"], "->", "PASS" if o["pass"] else "fail", f"| P(r_opt)/P(0)={o['ratio']:.2f}, peak at r={o['peak_r']}")
        print(f"fit f_hw={o['fit']['f']:.5f} [{o['fit']['f_ci95'][0]:.5f},{o['fit']['f_ci95'][1]:.5f}] p_noise={o['fit']['p_noise']:.3f}; billed {o['billed']}")
    print("echo by tier:", {k: round(v, 3) for k, v in echo.items()}, "H4 ordering holds:", out["H4_echo_ordering_A_gt_B_gt_C"])


if __name__ == "__main__":
    main()
