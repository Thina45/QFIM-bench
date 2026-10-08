"""Write the write-once manifest for Tiers B and C (campaigns/ladder_v2b/manifest.json).

Refuses unless a read-only account query shows remaining plan seconds >= BUDGET + RESERVE.
Predictions are exactly those in review/preregistration/ladder_predictions.json, written before any
Tier A data existed; nothing is re-fitted after seeing Tier A results.

    python analysis/adopt_tiers_bc.py
"""

import json
import os
from pathlib import Path

import numpy as np

from qfim_bench.backends import manifest_hash, verify_manifest_hash, write_campaign_manifest

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "review" / "preregistration"
OUTDIR = ROOT / "campaigns" / "ladder_v2b"
RUNS = 5
SEED_BASE = {"B": 20261108, "C": 20261208}  # fixed now; per-run offset added
BUDGET_S = 225      # tier B 105 + tier C 120 (about 21 s and 24 s per job, from Tier A's 20 s vs 16.8 s estimate)
RESERVE_S = 200
MAX_JOB_S = 30
PARENT_HASH = "6dcfc075d5e4af26a786ca2ee2cc911955f0104e6fb228da5c51bdd783bef3b9"
TIER_A_COMMIT = "ec88c30"


def remaining_seconds() -> float:
    from qiskit_ibm_runtime import QiskitRuntimeService

    s = QiskitRuntimeService(channel="ibm_quantum_platform", token=os.environ["IBM_QUANTUM_TOKEN"])
    return float(s.usage()["usage_remaining_seconds"])


def main() -> None:
    rem = remaining_seconds()
    print(f"remaining plan seconds: {rem}; need >= {BUDGET_S + RESERVE_S}")
    if rem < BUDGET_S + RESERVE_S:
        raise SystemExit("not enough remaining seconds to keep the reserve; refusing to write the manifest")

    pred = json.loads((PRE / "ladder_predictions.json").read_text(encoding="utf-8"))["circuits"]
    tiers = {"B": [c for c in pred if c["n"] == 4], "C": [c for c in pred if c["n"] == 5]}
    schedule = {}
    for t, cs in tiers.items():
        ids = [c["id"] for c in cs]
        for run in range(RUNS):
            rng = np.random.default_rng(SEED_BASE[t] + run)
            schedule[f"{t}_run_{run + 1}"] = [ids[i] for i in rng.permutation(len(ids))]

    pre = {
        "status": "ADOPTED - no job submitted at the time of writing",
        "adopted_utc_date": "2026-10-08",
        "unlocks": "Tiers B (n=4, M=2) and C (n=5, M=4) of campaigns/ladder_v2; approved in writing by the user "
                   "after the Tier A analysis",
        "parent_manifest_sha256": PARENT_HASH,
        "tier_A_results_commit": TIER_A_COMMIT,
        "predictions_note": "identical to review/preregistration/ladder_predictions.json, generated before any "
                            "Tier A data; not revised after Tier A",
        "criterion": {"file": "review/OPERATING_POINT_CRITERION.md", "commit": "c25b1b0",
                      "addendum": "review/OPERATING_POINT_ADDENDUM.md"},
        "hypotheses": {"H2": "n=4: criterion rules 1-4 met at r_opt=2 (simulator predicts 0.710)",
                       "H3": "n=5: criterion rules not met (simulator predicts 0.279 at r_opt)",
                       "H4": "echo P(all zeros) ordering n=3 > n=4 > n=5 (Tier A echo missed its band: 0.671 vs 0.806)"},
        "transpile": {"optimization_level": 3, "seed_transpiler": 42, "dd_sequence": "XpXm"},
        "layout": "chosen by the transpiler per job; physical qubits, calibration timestamp, depth and 2Q "
                  "counts recorded per job",
        "tolerance_rule": "band half-width = 5*sqrt(p(1-p)/8192) + 0.05; misses are reported",
        "design": {"runs_per_tier": RUNS, "circuits_per_run": 8, "one_job_per_run": True,
                   "order": {"method": "numpy default_rng(seed).permutation per run", "seed_base": SEED_BASE,
                             "schedule": schedule},
                   "order_of_tiers": "all of B, then all of C"},
        "budget": {"tier_B_cap_s": 105, "tier_C_cap_s": 120, "total_cap_s": BUDGET_S, "reserve_min_s": RESERVE_S,
                   "max_job_seconds": MAX_JOB_S,
                   "enforcement": "usage_budget_seconds and max_job_seconds in this manifest, HardwareBackend.run_batch"},
        "analysis": {"primary_uncertainty": "t-interval (95%, 4 d.f.) across the 5 runs; Wilson on pooled shots alongside",
                     "secondary": "fitted hardware fidelity per two-qubit gate vs simulator, per tier",
                     "reporting": "tolerance misses, null and negative results reported; a collapse at n=5 is a valid outcome"},
        "deviations_inherited": ["D1: the 5 runs per tier share one sitting (no day-to-day drift)",
                                 "D2: no git tag", "D3: CI not awaited"],
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = OUTDIR / "manifest.json"
    write_campaign_manifest(
        str(path),
        {c["id"]: round(c["prediction"], 5) for cs in tiers.values() for c in cs},
        note="ADOPTED. Tiers B and C of the ladder (mcz oracle, uniform start, matched diffusion, r=0..4, echo and readout controls).",
        max_jobs=2 * RUNS, shots=8192, usage_budget_seconds=BUDGET_S, max_job_seconds=MAX_JOB_S, preregistration=pre)
    m = json.loads(path.read_text(encoding="utf-8"))
    print("verify:", verify_manifest_hash(m), "| sha256:", m["sha256"], "| recomputed:", manifest_hash(m))


if __name__ == "__main__":
    main()
