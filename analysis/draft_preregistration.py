"""Build the DRAFT Phase 3 preregistration manifest. Nothing is submitted; the real manifest is
written later, by write_campaign_manifest, only after the user adopts the draft (checklist in
review/preregistration/ADOPTION_CHECKLIST.md).

Reads review/preregistration/ladder_predictions.json and writes
review/preregistration/ladder_v2_manifest_DRAFT.json, then prints its SHA-256.

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
CRITERION_COMMIT = "c25b1b0"
PROBE_CAP_S, TIER_A_CAP_S, RESERVE_MIN_S = 10, 150, 200
SIM_F_2Q = 0.9967  # fidelity per two-qubit gate fitted to the simulator, n=3 mcz (results/sim/fidelity_decay_fit.json)


def main() -> None:
    pred = json.loads((PRE / "ladder_predictions.json").read_text(encoding="utf-8"))
    circuits = pred["circuits"]
    tier = {"A": [c for c in circuits if c["n"] == 3],
            "B": [c for c in circuits if c["n"] == 4],
            "C": [c for c in circuits if c["n"] == 5]}
    ids_a = [c["id"] for c in tier["A"]]

    schedule = {}
    for day in range(DAYS):
        rng = np.random.default_rng(ORDER_SEED_BASE + day)
        schedule[f"day_{day + 1}"] = [ids_a[i] for i in rng.permutation(len(ids_a))]

    est_a = sum(c["estimated_seconds_per_8192_shots"] for c in tier["A"]) * DAYS
    body = {
        "predictions": {c["id"]: round(c["prediction"], 5) for c in tier["A"]},
        "note": "DRAFT. Active scope: probe + Tier A (n=3, M=1, mcz oracle, uniform start, matched diffusion, "
                "r=0..4, echo and readout controls). Tiers B and C are locked. Predictions are FakeMarrakesh "
                "(opt level 3) values from analysis/ladder_predictions.py.",
        "max_jobs": 1 + DAYS,
        "shots": pred["shots"],
        "usage_budget_seconds": PROBE_CAP_S + TIER_A_CAP_S,
        "max_job_seconds": TIER_A_CAP_S // DAYS,
        "preregistration": {
            "status": "DRAFT - not adopted, not submitted",
            "backend": "ibm_marrakesh (availability and remaining plan seconds re-checked at adoption)",
            "transpile": {"optimization_level": 3, "seed_transpiler": 42, "dd_sequence": "XpXm"},
            "layout": "chosen by the transpiler on each day from that day's calibration; physical qubits, "
                      "calibration timestamp and transpiled depth/2Q counts recorded for every job",
            "criterion": {"file": "review/OPERATING_POINT_CRITERION.md", "commit": CRITERION_COMMIT,
                          "addendum": "review/OPERATING_POINT_ADDENDUM.md"},
            "tolerance_rule": "band half-width = 5*sqrt(p(1-p)/8192) + 0.05 (values in "
                              "review/preregistration/ladder_predictions.json). Tolerance misses are reported.",
            "probe": {"circuits": "1 qubit, measure only", "jobs": 1, "cap_seconds": PROBE_CAP_S,
                      "excluded_from_analysis": True,
                      "purpose": "measure billed seconds for one tiny job before anything else",
                      "stop_rule": f"if the probe bills more than {PROBE_CAP_S} s, stop and re-plan"},
            "budget": {
                "tier_A_cap_seconds": TIER_A_CAP_S,
                "probe_plus_tier_A_cap_seconds": PROBE_CAP_S + TIER_A_CAP_S,
                "tier_B": "LOCKED", "tier_C": "LOCKED",
                "unlock": "separate written approval after Tier A analysis; new manifest, new hash, new tag",
                "reserve_min_seconds": RESERVE_MIN_S,
                "reserve_rule": f"adopt only if remaining plan seconds >= {PROBE_CAP_S + TIER_A_CAP_S + RESERVE_MIN_S}; "
                                f"at least {RESERVE_MIN_S} s must remain unspent after this manifest",
                "enforcement": "usage_budget_seconds (cumulative billed seconds) and max_job_seconds "
                               "(per-job runtime limit) in this manifest, enforced by HardwareBackend.run_batch",
            },
            "design": {"circuits_per_day_tier_A": len(ids_a), "one_job_per_day": True, "days": DAYS,
                       "repeats_are_days": True,
                       "order_randomisation": {"method": "numpy default_rng(seed).permutation, per day",
                                               "seed_base": ORDER_SEED_BASE, "schedule": schedule}},
            "tier_stop_rule": "If, over the 5 days, no Tier A ladder cell reaches 3x its r=0 value at r_opt, "
                              "stop and report where amplification disappears.",
            "record_per_job": ["job_id", "calibration timestamp", "physical qubits", "transpiled depth",
                               "transpiled 2Q count", "billed usage_seconds", "queue time"],
            "analysis": {
                "primary_uncertainty": "t-interval (95%, 4 d.f., t=2.776) across the 5 daily values of each "
                                       "quantity; shot-noise Wilson intervals reported alongside, not instead",
                "primary": "marked-state probability per cell vs prediction band; TVD to prediction with null "
                           "floor and p-value; offset from M/N in standard errors",
                "secondary": f"fit hardware fidelity per two-qubit gate (qfim_bench.fit) and compare with the "
                             f"simulator's {SIM_F_2Q}; echo and readout controls reported alongside",
                "reporting": "tolerance misses, null and negative results are reported",
            },
            "estimated_execution_seconds_tier_A": round(est_a, 1),
            "estimate_caveat": "execution time only; billed time includes per-job overhead and is measured "
                               "by the probe",
            "git_tag_to_create_on_adoption": "prereg-ladder-v2",
        },
    }
    out = PRE / "ladder_v2_manifest_DRAFT.json"
    out.write_text(json.dumps(body, indent=2), encoding="utf-8")
    print(f"Tier A: {len(ids_a)} circuits x {DAYS} days, est. execution {est_a:.0f} s; draft sha256: {manifest_hash(body)}")


if __name__ == "__main__":
    main()
