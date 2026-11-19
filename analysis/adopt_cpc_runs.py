"""Adopt the committed CPC-revision draft manifests (review/preregistration/cpc_run{1,2,4}_manifest_DRAFT.json)
into real campaign manifests under campaigns/, exactly as campaigns/ladder_v2(/b) were adopted from their
own DRAFT files. write_campaign_manifest() refuses to overwrite, so re-running this is a no-op once adopted.

    python analysis/adopt_cpc_runs.py
"""
import json
from pathlib import Path

import numpy as np

from qfim_bench.backends import write_campaign_manifest

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "review" / "preregistration"

TIER_LABELS = {
    "A": ["ladder_n3_M1_r0", "ladder_n3_M1_r1", "ladder_n3_M1_r2", "ladder_n3_M1_r3", "ladder_n3_M1_r4",
          "echo_n3_M1_r2", "readout_n3_zeros", "readout_n3_ones"],
    "B": ["ladder_n4_M2_r0", "ladder_n4_M2_r1", "ladder_n4_M2_r2", "ladder_n4_M2_r3", "ladder_n4_M2_r4",
          "echo_n4_M2_r2", "readout_n4_zeros", "readout_n4_ones"],
    "C": ["ladder_n5_M4_r0", "ladder_n5_M4_r1", "ladder_n5_M4_r2", "ladder_n5_M4_r3", "ladder_n5_M4_r4",
          "echo_n5_M4_r2", "readout_n5_zeros", "readout_n5_ones"],
}


def schedule_for(tiers: list[str], runs: int, seed_base: int) -> dict:
    sched = {}
    for tier in tiers:
        for run in range(1, runs + 1):
            rng = np.random.default_rng(seed_base + hash(tier) % 1000 + run)
            order = list(rng.permutation(TIER_LABELS[tier]))
            sched[f"{tier}_run_{run}"] = order
    return sched


def adopt(run_name: str, draft_name: str, tiers: list[str], runs: int, backend: str,
          dd_sequence: str, seed_base: int) -> None:
    out_path = ROOT / "campaigns" / run_name / "manifest.json"
    if out_path.exists():
        print(f"{run_name}: already adopted at {out_path}, skipping")
        return
    draft = json.loads((DRAFTS / draft_name).read_text(encoding="utf-8"))
    predictions = draft["predictions_fakemarrakesh"] if "predictions_fakemarrakesh" in draft else {
        k: v for k, v in draft["predictions"]["fakemarrakesh_dd_on_reference_only"].items()
    }
    max_jobs = runs * len(tiers)
    usage_budget = draft["usage_budget_seconds"]
    preregistration = {
        "status": "ADOPTED - no job submitted at the time of writing",
        "backend": f"{backend} (live calibration)",
        "transpile": {"optimization_level": 3, "seed_transpiler": 42, "dd_sequence": dd_sequence},
        "layout": "chosen by the transpiler at submission time from that device's live calibration; "
                  "transpiled once per (tier, device) and reused for every repeat within this manifest",
        "tiers": tiers,
        "repeats_per_tier": runs,
        "design": {"order": {"schedule": schedule_for(tiers, runs, seed_base)}},
        "addendum": "review/OPERATING_POINT_ADDENDUM_V3.md",
        "draft_source": f"review/preregistration/{draft_name}",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_campaign_manifest(
        str(out_path),
        predictions=predictions,
        note=draft["note"].replace("DRAFT.", "ADOPTED."),
        max_jobs=max_jobs,
        shots=8192,
        preregistration=preregistration,
        usage_budget_seconds=usage_budget,
        max_job_seconds=30,
    )
    print(f"{run_name}: adopted -> {out_path}")


if __name__ == "__main__":
    adopt("cpc_run1", "cpc_run1_manifest_DRAFT.json", ["A", "B", "C"], 5, "ibm_marrakesh", "XpXm", seed_base=20261119)
    adopt("cpc_run2", "cpc_run2_manifest_DRAFT.json", ["B"], 5, "ibm_marrakesh", "NONE", seed_base=20261120)
    adopt("cpc_run4", "cpc_run4_manifest_DRAFT.json", ["A", "B", "C"], 5, "ibm_kingston", "XpXm", seed_base=20261121)
