"""CPC revision, Phase 1 A-D and F: classical baseline, global/per-size depolarizing fit, echo-decay
vs Grover fit, TVD/Hellinger distances, and the diffusion-pitfall comparison. Read-only with respect
to hardware: only already-saved campaign/manifest/results files are used, no circuits are run.

Deviation D1 (established in Phase 0): the "5 days" of ladder_v2/ladder_v2b are 5 jobs submitted in
one sitting on 2026-10-08, not 5 separate calibration days; Tier A shares one calibration timestamp,
Tier B and Tier C runs 1-3 share one, and Tier C runs 4-5 used a later one. This script's t-intervals
therefore describe within-sitting shot-to-shot spread across repeated submissions, not day-to-day
drift, exactly as analysis/analyze_ladder_tierA.py and analyze_ladder_tiersBC.py already state.

    python analysis/phase1_cpc_revision.py
"""

import csv
import json
import math
from pathlib import Path

import numpy as np

from qfim_bench.fit import decay_model, fit_fidelity_decay
from qfim_bench.search_cost import classical_query_success_probability
from qfim_bench.tvd_calibration import counts_vector, hellinger, tvd, tvd_pvalue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "cpc_revision"
OUT.mkdir(parents=True, exist_ok=True)

TIERS = {
    "A": {"n": 3, "M": 1, "dir": ROOT / "results" / "hardware" / "ladder_v2", "files": [f"day{d}.json" for d in range(1, 6)]},
    "B": {"n": 4, "M": 2, "dir": ROOT / "results" / "hardware" / "ladder_v2b", "files": [f"B_run{r}.json" for r in range(1, 6)]},
    "C": {"n": 5, "M": 4, "dir": ROOT / "results" / "hardware" / "ladder_v2b", "files": [f"C_run{r}.json" for r in range(1, 6)]},
}
R_RANGE = range(0, 5)
T975_DF4 = 2.7764451051977987

PREDICTIONS = {
    c["id"]: c
    for c in json.loads((ROOT / "review" / "preregistration" / "ladder_predictions.json").read_text())["circuits"]
}


def marked_bitstrings(cid: str, n: int) -> set[str]:
    """Marked computational-basis bitstrings for a circuit id, from the actual preregistered marked
    indices (review/preregistration/ladder_predictions.json) -- NOT assumed as range(M)."""
    return {format(i, f"0{n}b") for i in PREDICTIONS[cid]["marked"]}


def load_runs(tier: str) -> list[dict]:
    spec = TIERS[tier]
    return [json.loads((spec["dir"] / f).read_text(encoding="utf-8")) for f in spec["files"]]


def pooled_ladder_counts(tier: str, r: int) -> tuple[dict, int, int, float, list]:
    """Pooled hardware counts for the ladder_n{n}_M{M}_r{r} circuit, marked-state hits/shots, mean 2Q
    gate count, and the layouts used across the tier's 5 runs."""
    spec = TIERS[tier]
    n, M = spec["n"], spec["M"]
    cid = f"ladder_n{n}_M{M}_r{r}"
    runs = load_runs(tier)
    marked = marked_bitstrings(cid, n)
    pooled, tot_k, tot_n, gates, layouts = {}, 0, 0, [], []
    for d in runs:
        c = d["counts"][cid]
        info = next(i for i, lbl in zip(d["job"]["circuits_info"], d["job"]["labels"]) if lbl == cid)
        gates.append(info["two_qubit_gates"])
        layouts.append(tuple(info["physical_qubits"]))
        for key, x in c.items():
            pooled[key] = pooled.get(key, 0) + x
        tot_k += sum(x for key, x in c.items() if key in marked)
        tot_n += sum(c.values())
    return pooled, tot_k, tot_n, float(np.mean(gates)), sorted(set(layouts))


def per_run_means(tier: str, r: int) -> list[float]:
    spec = TIERS[tier]
    n, M = spec["n"], spec["M"]
    cid = f"ladder_n{n}_M{M}_r{r}"
    marked = marked_bitstrings(cid, n)
    out = []
    for d in load_runs(tier):
        c = d["counts"][cid]
        k, t = sum(x for key, x in c.items() if key in marked), sum(c.values())
        out.append(k / t)
    return out


def ideal_probability(M: int, N: int, r: int) -> float:
    from qfim_bench.circuit import theoretical_success_probability

    return theoretical_success_probability(M, N, r)


# --------------------------------------------------------------------------
# Phase 1A: classical query baseline
# --------------------------------------------------------------------------

def phase1a() -> list[dict]:
    rows = []
    for tier, spec in TIERS.items():
        n, M = spec["n"], spec["M"]
        N = 2**n
        for r in R_RANGE:
            vals = per_run_means(tier, r)
            mean, sd = float(np.mean(vals)), float(np.std(vals, ddof=1))
            half = T975_DF4 * sd / math.sqrt(5)
            lo, hi = mean - half, mean + half
            pc = classical_query_success_probability(M, N, r)
            rows.append({
                "tier": tier, "n": n, "M": M, "N": N, "r": r,
                "hw_mean": mean, "hw_t_ci95_lo": lo, "hw_t_ci95_hi": hi,
                "classical_Pc": pc,
                "better_than_classical": lo > pc,
            })
    with (OUT / "phase1a_classical_baseline.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


# --------------------------------------------------------------------------
# Phase 1B: per-size and global depolarizing fit
# --------------------------------------------------------------------------

N_FIT_PARAMS = 2  # f, p_noise


def _residuals_and_chi_square(g_list, ideal_list, k_list, n_list, f, p_noise, rows, extra):
    """Residual (hw mean - fit) and binomial chi-square per point; returns (rows_appended, reduced_chi2)."""
    chi2 = 0.0
    for g, pideal, k, tot_n in zip(g_list, ideal_list, k_list, n_list):
        p_fit = float(decay_model(np.array([g]), np.array([pideal]), f, p_noise)[0])
        hw_mean = k / tot_n
        var = p_fit * (1 - p_fit) / tot_n
        term = (hw_mean - p_fit) ** 2 / var if var > 0 else 0.0
        chi2 += term
        rows.append({**extra, "two_qubit_gates": g, "hw_mean": hw_mean, "fit_prediction": p_fit,
                     "residual": hw_mean - p_fit, "chi2_term": term})
    dof = len(g_list) - N_FIT_PARAMS
    reduced = chi2 / dof if dof > 0 else float("nan")
    return chi2, dof, reduced


def phase1b() -> dict:
    per_size = {}
    all_g, all_ideal, all_k, all_n = [], [], [], []
    peak_check = {}
    residual_rows: list[dict] = []
    for tier, spec in TIERS.items():
        n, M = spec["n"], spec["M"]
        N = 2**n
        g_list, ideal_list, k_list, n_list, means = [], [], [], [], []
        for r in R_RANGE:
            pooled, k, tot_n, gates, _ = pooled_ladder_counts(tier, r)
            g_list.append(gates)
            ideal_list.append(ideal_probability(M, N, r))
            k_list.append(k)
            n_list.append(tot_n)
            means.append(k / tot_n)
        fit = fit_fidelity_decay(g_list, ideal_list, k_list, n_list, n_bootstrap=300, seed=1)
        r_opt_hw = int(np.argmax(means))
        chi2, dof, reduced_chi2 = _residuals_and_chi_square(
            g_list, ideal_list, k_list, n_list, fit.f, fit.p_noise, residual_rows,
            {"tier": tier, "r": None})
        # fill in r per row just appended (last len(R_RANGE) rows, in R_RANGE order)
        for row, r in zip(residual_rows[-len(R_RANGE):], R_RANGE):
            row["r"] = r
        per_size[tier] = {
            "n": n, "M": M, "N": N,
            "f": fit.f, "f_ci95": list(fit.f_ci),
            "p_noise": fit.p_noise, "p_noise_ci95": list(fit.p_noise_ci),
            "r_opt_hardware": r_opt_hw,
            "hw_means_by_r": means,
            "chi_square": chi2, "degrees_of_freedom": dof, "reduced_chi_square": reduced_chi2,
        }
        all_g.extend(g_list)
        all_ideal.extend(ideal_list)
        all_k.extend(k_list)
        all_n.extend(n_list)
        peak_check[tier] = r_opt_hw

    global_fit = fit_fidelity_decay(all_g, all_ideal, all_k, all_n, n_bootstrap=300, seed=1)
    global_chi2, global_dof, global_reduced = _residuals_and_chi_square(
        all_g, all_ideal, all_k, all_n, global_fit.f, global_fit.p_noise, [], {})
    expected_peaks = {"A": 2, "B": 1, "C": 1}
    out = {
        "per_size": per_size,
        "global": {"f": global_fit.f, "f_ci95": list(global_fit.f_ci),
                   "p_noise": global_fit.p_noise, "p_noise_ci95": list(global_fit.p_noise_ci),
                   "chi_square": global_chi2, "degrees_of_freedom": global_dof,
                   "reduced_chi_square": global_reduced},
        "expected_peak_r": expected_peaks,
        "observed_peak_r": peak_check,
        "peaks_match": {t: expected_peaks[t] == peak_check[t] for t in TIERS},
    }
    (OUT / "phase1b_global_fit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (OUT / "phase1b_residuals.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(residual_rows[0].keys()))
        w.writeheader()
        w.writerows(residual_rows)
    return out


# --------------------------------------------------------------------------
# Phase 1C: echo-circuit fidelity decay vs the depolarizing fit (EXPLORATORY echo data)
# --------------------------------------------------------------------------

def phase1c(fit_result: dict) -> list[dict]:
    echo = json.loads((ROOT / "results" / "hardware" / "echo_fidelity_exploratory.json").read_text())
    rows = []
    tier_by_n = {spec["n"]: tier for tier, spec in TIERS.items()}
    for e in echo["echo"]:
        n = e["n"]
        tier = tier_by_n[n]
        rows.append({
            "status": "EXPLORATORY",
            "n": n, "tier": tier,
            "echo_two_qubit_gates": e["echo_2q_gates"],
            "P_echo": e["P_echo"], "P_ci95_lo": e["P_ci95"][0], "P_ci95_hi": e["P_ci95"][1],
            "f_echo": e["f_echo"], "f_echo_ci95_lo": e["f_ci95"][0], "f_echo_ci95_hi": e["f_ci95"][1],
            "f_grover_fit_persize": fit_result["per_size"][tier]["f"],
            "f_simulator": e["f_simulator"],
        })
    with (OUT / "phase1c_echo_vs_grover_fit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


# --------------------------------------------------------------------------
# Phase 1D: TVD and Hellinger distances to ideal and to the FakeMarrakesh noisy simulator
# --------------------------------------------------------------------------

def phase1d() -> list[dict]:
    sweep = json.loads((ROOT / "results" / "sim" / "feasibility_sweep.json").read_text())
    rows = []
    for tier, spec in TIERS.items():
        n, M = spec["n"], spec["M"]
        N = 2**n
        for r in R_RANGE:
            pooled, k, tot_n, gates, layouts = pooled_ladder_counts(tier, r)
            hw_vec = counts_vector(pooled, n) / tot_n

            cid = f"ladder_n{n}_M{M}_r{r}"
            marked_idx = [int(s, 2) for s in marked_bitstrings(cid, n)]
            p_marked = ideal_probability(M, N, r)
            ideal_vec = np.full(N, (1.0 - p_marked) / (N - M))
            for i in marked_idx:
                ideal_vec[i] = p_marked / M

            sim_point = [x for x in sweep["points"] if x["style"] == "mcz" and x["n"] == n and x["M"] == M and x["r"] == r]
            row = {"tier": tier, "n": n, "r": r, "two_qubit_gates": gates,
                   "tvd_hw_vs_ideal": tvd(hw_vec, ideal_vec), "hellinger_hw_vs_ideal": hellinger(hw_vec, ideal_vec)}
            if sim_point:
                sim_counts: dict = {}
                for cc in sim_point[0]["noisy_counts"]:
                    for key, x in cc.items():
                        sim_counts[key] = sim_counts.get(key, 0) + x
                sim_total = sum(sim_counts.values())
                sim_vec = counts_vector(sim_counts, n) / sim_total
                row["tvd_hw_vs_noisy_sim"] = tvd(hw_vec, sim_vec)
                row["hellinger_hw_vs_noisy_sim"] = hellinger(hw_vec, sim_vec)
                pv = tvd_pvalue(counts_vector(pooled, n), ideal_vec, draws=2000, seed=1)
                row["tvd_hw_vs_ideal_null_floor"] = pv["null_floor"]
                row["tvd_hw_vs_ideal_p_value"] = pv["p_value"]
            else:
                row["tvd_hw_vs_noisy_sim"] = None
                row["hellinger_hw_vs_noisy_sim"] = None
                row["tvd_hw_vs_ideal_null_floor"] = None
                row["tvd_hw_vs_ideal_p_value"] = None
            rows.append(row)
    with (OUT / "phase1d_distances.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


# --------------------------------------------------------------------------
# Phase 1F: diffusion pitfall (matched vs Hadamard diffusion, 30 seeds)
# --------------------------------------------------------------------------

def phase1f() -> list[dict]:
    data = json.loads((ROOT / "results" / "sim" / "start_state_design.json").read_text())
    by_key = {}
    for e in data["noiseless"]:
        by_key.setdefault((e["M"], e["r"]), {})[e["start"]] = e
    rows = []
    for (M, r), entry in sorted(by_key.items()):
        matched = entry.get("ansatz_matched")
        hadamard = entry.get("ansatz_hadamard")
        if matched is None or hadamard is None:
            continue
        rows.append({
            "M": M, "r": r,
            "matched_median": matched["summary"]["median"],
            "matched_q1": matched["summary"]["q1"], "matched_q3": matched["summary"]["q3"],
            "hadamard_median": hadamard["summary"]["median"],
            "hadamard_q1": hadamard["summary"]["q1"], "hadamard_q3": hadamard["summary"]["q3"],
            "n_seeds": hadamard["summary"]["n"],
            "degradation_median": matched["summary"]["median"] - hadamard["summary"]["median"],
        })
    with (OUT / "phase1f_diffusion_pitfall.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def main() -> None:
    a = phase1a()
    print(f"Phase 1A: {len(a)} rows -> {OUT / 'phase1a_classical_baseline.csv'}")
    for r in a:
        print(f"  tier {r['tier']} r={r['r']:d}  hw={r['hw_mean']:.4f} [{r['hw_t_ci95_lo']:.4f},{r['hw_t_ci95_hi']:.4f}]  "
              f"Pc={r['classical_Pc']:.4f}  better_than_classical={r['better_than_classical']}")

    b = phase1b()
    print(f"\nPhase 1B -> {OUT / 'phase1b_global_fit.json'}")
    for tier, d in b["per_size"].items():
        print(f"  tier {tier} (n={d['n']}): f={d['f']:.5f} CI{d['f_ci95']}  r_opt_hw={d['r_opt_hardware']}")
    print(f"  global: f={b['global']['f']:.5f} CI{b['global']['f_ci95']}")
    print(f"  peak match: {b['peaks_match']}")

    c = phase1c(b)
    print(f"\nPhase 1C (EXPLORATORY echo data) -> {OUT / 'phase1c_echo_vs_grover_fit.csv'}")
    for r in c:
        print(f"  n={r['n']}: f_echo={r['f_echo']:.4f}  f_grover_fit={r['f_grover_fit_persize']:.4f}  f_sim={r['f_simulator']:.4f}")

    d = phase1d()
    print(f"\nPhase 1D -> {OUT / 'phase1d_distances.csv'} ({len(d)} rows)")

    f = phase1f()
    print(f"\nPhase 1F -> {OUT / 'phase1f_diffusion_pitfall.csv'} ({len(f)} rows)")
    for row in f:
        print(f"  M={row['M']} r={row['r']}: matched={row['matched_median']:.4f} hadamard={row['hadamard_median']:.4f} "
              f"degradation={row['degradation_median']:.4f}")


if __name__ == "__main__":
    main()
