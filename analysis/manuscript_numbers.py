"""Export results/cpc_revision/numbers_for_manuscript.json: every number the manuscript should
quote, each tagged with its source file. No new hardware runs; reads only existing analysis
outputs (and recomputes the H1 gate-count confound and the effective-error ratios inline, since
neither existed as a saved number before this pass).

    python analysis/manuscript_numbers.py
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CPC = ROOT / "results" / "cpc_revision"


def _load(name: str):
    return json.loads((CPC / name).read_text(encoding="utf-8"))


def h1_confound() -> dict:
    """At the H1 cell (n=3, r=2), Run 3's circuit had 45 two-qubit gates vs Run 1's 39. Using
    Run 1's own per-size fit (f, p_noise) and the exact ideal probability for this circuit,
    predict the success-probability change from that gate-count difference alone, and compare
    with the observed |Run 1 mean - Run 3 mean|."""
    from qfim_bench.circuit import theoretical_success_probability
    from qfim_bench.fit import decay_model

    fit = _load("cpc_run1_fit.json")["per_size"]["A"]
    f, p_noise = fit["f"], fit["p_noise"]
    p_ideal = theoretical_success_probability(1, 8, 2)  # n=3, M=1, r=2
    g_run1, g_run3 = 39, 45
    p_run1_pred = float(decay_model(np.array([g_run1]), np.array([p_ideal]), f, p_noise)[0])
    p_run3_pred = float(decay_model(np.array([g_run3]), np.array([p_ideal]), f, p_noise)[0])
    predicted_diff = p_run3_pred - p_run1_pred  # negative: more gates -> lower success

    runs = _load("cpc_runs_analysis.json")
    obs_run1 = runs["cpc_run1"]["A"]["ladder_n3_M1_r2"]["mean"]
    obs_run3 = runs["cpc_run3"]["A"]["ladder_n3_M1_r2"]["mean"]
    observed_diff = obs_run3 - obs_run1

    # gate-matched tier B comparison (113 = 113 two-qubit gates, no confound)
    b1 = runs["cpc_run1"]["B"]["ladder_n4_M2_r2"]
    b3 = runs["cpc_run3"]["B"]["ladder_n4_M2_r2"]
    b1_half = (b1["t_ci95"][1] - b1["t_ci95"][0]) / 2

    return {
        "cell": "ladder_n3_M1_r2 (n=3, r=2) -- the H1 cell",
        "run1_two_qubit_gates": g_run1, "run3_two_qubit_gates": g_run3,
        "fit_used": "cpc_run1_fit.json per_size.A (Run 1's own n=3 fit)",
        "p_ideal": p_ideal, "f": f, "p_noise": p_noise,
        "predicted_p_at_run1_gates": p_run1_pred, "predicted_p_at_run3_gates": p_run3_pred,
        "predicted_diff_from_gate_count_alone": predicted_diff,
        "observed_run1_mean": obs_run1, "observed_run3_mean": obs_run3,
        "observed_diff": observed_diff,
        "conclusion": (
            "the gate-count increase alone predicts a drop of "
            f"{abs(predicted_diff):.5f}, which is LARGER in magnitude than the observed "
            f"difference of {abs(observed_diff):.5f} -- the gate-count change can account for "
            "the entire observed H1 difference at n=3; H1 at n=3 is confounded and provides no "
            "clean evidence of day-to-day drift"
        ),
        "gate_matched_alternative": {
            "cell": "ladder_n4_M2_r2 (n=4, r=2) -- identical two-qubit gate count both runs (113=113)",
            "run1_mean": b1["mean"], "run3_mean": b3["mean"],
            "diff": b3["mean"] - b1["mean"],
            "run1_ci_half_width": b1_half,
            "supported": abs(b3["mean"] - b1["mean"]) > b1_half,
            "note": "supplementary evidence, outside H1's preregistered n=3-only scope, but the "
                     "only gate-matched (unconfounded) drift comparison available",
        },
        "source": "computed in analysis/manuscript_numbers.py from cpc_run1_fit.json, "
                   "cpc_runs_analysis.json, results/cpc_revision/run3_layout_comparison.json",
    }


def effective_error_ratios() -> dict:
    oct8_fit = _load("phase1b_global_fit.json")["global"]
    run1_fit = _load("cpc_run1_fit.json")["global"]
    run4_fit = _load("cpc_run4_fit.json")["global"]
    hist = _load("historical_calibration.json")
    med = _load("run1_run4_median_2q_error.json")

    oct8_err = float(np.median([g["error"] for k in ["tierA_n3", "tierB_n4", "tierC_run1-3_n5"]
                                 for g in hist[k]["two_qubit_gate_errors"]]))
    run1_err = med["run1_by_calibration"]["2026-11-19 14:35:58+05:30"][1]
    run4_err = med["run4"][1]

    out = {}
    for label, fit, err in [("oct8_marrakesh_2026-10-08", oct8_fit, oct8_err),
                             ("run1_marrakesh_2026-11-19", run1_fit, run1_err),
                             ("run4_kingston_2026-11-19", run4_fit, run4_err)]:
        f = fit["f"]
        lo, hi = fit["f_ci_inflated"] if "f_ci_inflated" in fit else fit["f_ci95_inflated"]
        ratio = (1 - f) / err
        ratio_lo, ratio_hi = (1 - hi) / err, (1 - lo) / err
        out[label] = {
            "one_minus_f": 1 - f, "median_two_qubit_error_used_qubits": err,
            "ratio": ratio, "ratio_ci_from_inflated_f_ci": [ratio_lo, ratio_hi],
        }
    out["note"] = ("effective error per two-qubit gate (1-f) is roughly 2.7-3.4x the calibrated "
                    "two-qubit error on the qubits actually used, across two devices and two "
                    "dates -- an observation with only 3 points, not a law")
    out["source"] = ("phase1b_global_fit.json, cpc_run1_fit.json, cpc_run4_fit.json (f, inflated "
                      "CI), historical_calibration.json + run1_run4_median_2q_error.json "
                      "(median two-qubit error)")
    return out


def main() -> None:
    out = {
        "phase1a_classical_baseline": {
            "file": "results/cpc_revision/phase1a_classical_baseline.csv",
            "note": "classical query-search baseline per (tier, r); q=0 bug fixed (section 2 of REPORT.md)",
        },
        "phase1b_fits": {
            "oct8": {"file": "results/cpc_revision/phase1b_global_fit.json",
                     "note": "per-size A/B/C + global depolarizing fit, with chi-square and "
                              "f_ci95_inflated (sqrt(reduced_chi_square)) added this pass"},
            "run1": {"file": "results/cpc_revision/cpc_run1_fit.json",
                     "note": "chi-square + f_ci_inflated added this pass (was missing before)"},
            "run4": {"file": "results/cpc_revision/cpc_run4_fit.json",
                     "note": "chi-square + f_ci_inflated added this pass (was missing before)"},
            "goodness_of_fit": "reduced chi-square is 15-250 across all fits (far above 1); the "
                "model is phenomenological -- it captures the trend and the peak-r shift, not an "
                "exact fit within shot noise. Use f_ci*_inflated, not the raw bootstrap CI, for "
                "any CI quoted in the manuscript.",
        },
        "phase1c_echo_vs_grover": {"file": "results/cpc_revision/phase1c_echo_vs_grover_fit.csv"},
        "phase1d_tvd_hellinger": {
            "file": "results/cpc_revision/phase1d_distances.csv",
            "note": "per (tier, r): TVD and Hellinger distance, hardware vs ideal and hardware "
                     "vs FakeMarrakesh noisy simulator, plus a TVD null-floor/p-value",
        },
        "phase1e_digital_twin": {
            "file": "results/cpc_revision/phase1e_digital_twin.json",
            "note": "calibration-day digital twin (gate_error + readout_error only, no thermal "
                     "relaxation -- device BackendProperties has no frequency field) vs generic "
                     "FakeMarrakesh, TVD per cell",
        },
        "phase1f_diffusion_pitfall": {"file": "results/cpc_revision/phase1f_diffusion_pitfall.csv"},
        "run1_billing": {"file": "results/cpc_revision/billing_correction.json", "value_s": 325.0},
        "run2_billing": {"file": "results/cpc_revision/billing_correction.json", "value_s": 100.0},
        "run3_billing": {"file": "campaigns/cpc_run3/manifest.json", "value_s": 195.0},
        "run4_billing": {"file": "results/cpc_revision/billing_correction.json", "value_s": 315.0},
        "run1_vs_run4_criterion": {"file": "results/cpc_revision/cpc_run1_criterion.json / cpc_run4_criterion.json"},
        "h1": h1_confound(),
        "h2": {
            "file": "results/cpc_revision/REPORT.md section 7",
            "verdict": "NOT SUPPORTED -- r=1 significant in the opposite direction (DD off beats DD on)",
        },
        "effective_error_ratio": effective_error_ratios(),
    }
    out_path = CPC / "numbers_for_manuscript.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
