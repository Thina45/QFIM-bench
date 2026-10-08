"""Build the DRAFT Phase 3 preregistration manifest. Nothing is submitted; the real manifest is
written later, by write_campaign_manifest, only after the user approves the QPU budget.

Reads review/preregistration/ladder_predictions.json and writes
review/preregistration/ladder_v2_manifest_DRAFT.json, plus prints its SHA-256 (the value that the
git tag and the real manifest would carry if the draft were adopted unchanged).

    python analysis/draft_preregistration.py
"""

import json
from pathlib import Path

import numpy as np

from qfim_bench.backends import manifest_hash

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "review" / "preregistration"
DAYS = 5
ORDER_SEED_BASE = 20261008  # + day index; fixed now so the order cannot be chosen after seeing data
CRITERION_COMMIT = "c25b1b0"  # review/OPERATING_POINT_CRITERION.md, committed before the sweep


def main() -> None:
    pred = json.loads((PRE / "ladder_predictions.json").read_text(encoding="utf-8"))
    circuits = pred["circuits"]
    ids = [c["id"] for c in circuits]

    schedule = {}
    for day in range(DAYS):
        rng = np.random.default_rng(ORDER_SEED_BASE + day)
        schedule[f"day_{day + 1}"] = [ids[i] for i in rng.permutation(len(ids))]

    tiers = {
        "A": [c["id"] for c in circuits if c["n"] == 3],
        "B": [c["id"] for c in circuits if c["n"] == 4],
        "C": [c["id"] for c in circuits if c["n"] == 5],
    }
    total_runs = len(circuits) * DAYS
    est_seconds = pred["estimated_execution_seconds_per_repeat"] * DAYS

    body = {
        "predictions": {c["id"]: round(c["prediction"], 5) for c in circuits},
        "note": "DRAFT. Ladder (3,1),(4,2),(5,4), mcz oracle, uniform start, matched diffusion, r=0..r_opt+2, "
                "with echo and readout controls. Predictions are FakeMarrakesh (opt level 3) means from "
                "results/sim/feasibility_sweep.json; echo/readout from analysis/ladder_predictions.py.",
        "max_jobs": total_runs,
        "shots": pred["shots"],
        "preregistration": {
            "status": "DRAFT - not adopted, not submitted",
            "backend": "ibm_marrakesh (availability to be confirmed against the account before adoption)",
            "transpile": {"optimization_level": 3, "seed_transpiler": 42, "dd_sequence": "XpXm"},
            "criterion_file": "review/OPERATING_POINT_CRITERION.md",
            "criterion_commit": CRITERION_COMMIT,
            "addendum_file": "review/OPERATING_POINT_ADDENDUM.md",
            "tolerance_rule": "band half-width = 5*sqrt(p(1-p)/8192) + 0.05; per-circuit values in "
                              "review/preregistration/ladder_predictions.json",
            "circuits_per_repeat": len(circuits),
            "repeats_days": DAYS,
            "one_repeat_per_day": True,
            "order_randomisation": {"method": "numpy default_rng(seed).permutation of circuit ids, per day",
                                    "seed_base": ORDER_SEED_BASE, "schedule": schedule},
            "tiers": tiers,
            "tier_stop_rule": "Run tier A first (all days). If, over its repeats, no ladder cell reaches "
                              "3x its r=0 measurement at r_opt, stop: report where amplification disappears; "
                              "do not run tiers B and C without a new approval.",
            "record_per_job": ["job_id", "backend calibration timestamp", "qubit layout", "transpiled depth",
                               "transpiled 2Q count", "queue and execution time"],
            "analysis_plan": "TVD to prediction with null floor and p-value (tvd_calibration), marked-state "
                             "probability with Wilson 95% interval, fidelity-decay fit, offset from M/N in "
                             "standard errors, echo and readout controls reported alongside. Negative and "
                             "null results are reported.",
            "git_tag_to_create_on_adoption": "prereg-ladder-v2",
            "estimated_execution_seconds_total": round(est_seconds, 1),
            "estimate_caveat": "execution time only (scheduled circuit duration + 250 us repetition delay "
                               "per shot); per-job overhead and billing granularity unknown until one tiny "
                               "job is measured after approval.",
        },
    }
    out = PRE / "ladder_v2_manifest_DRAFT.json"
    out.write_text(json.dumps(body, indent=2), encoding="utf-8")
    print(f"{len(circuits)} circuits/repeat x {DAYS} days = {total_runs} circuit-runs; "
          f"est. execution {est_seconds:.0f} s ({est_seconds / 60:.1f} min)")
    for t, cs in tiers.items():
        s = sum(c["estimated_seconds_per_8192_shots"] for c in circuits if c["id"] in cs) * DAYS
        print(f"  tier {t}: {len(cs)} circuits x {DAYS} = {len(cs) * DAYS} runs, est. {s:.0f} s")
    print("draft sha256:", manifest_hash(body))


if __name__ == "__main__":
    main()
