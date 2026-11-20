"""Adopt the committed Run 3 draft manifest (review/preregistration/cpc_run3_manifest_DRAFT.json)
into campaigns/cpc_run3/manifest.json, exactly as adopt_cpc_runs.py adopted Run 1/2/4. Records the
pinned-layout re-transpilation deviation (Run 1's own transpiled circuits were never saved, so Run 3
pins initial_layout to Run 1's recorded physical qubits instead of reusing saved circuits) in the
preregistration block, and records the QPY index built by prepare_run3.py.

    python analysis/adopt_run3.py
"""
import json
from pathlib import Path

import numpy as np

from qfim_bench.backends import write_campaign_manifest

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "review" / "preregistration" / "cpc_run3_manifest_DRAFT.json"
LAYOUT_COMPARISON = ROOT / "results" / "cpc_revision" / "run3_layout_comparison.json"
QPY_INDEX = ROOT / "campaigns" / "cpc_run3" / "qpy" / "index.json"
OUT = ROOT / "campaigns" / "cpc_run3" / "manifest.json"

TIER_LABELS = {
    "A": ["ladder_n3_M1_r0", "ladder_n3_M1_r1", "ladder_n3_M1_r2", "ladder_n3_M1_r3", "ladder_n3_M1_r4",
          "echo_n3_M1_r2", "readout_n3_zeros", "readout_n3_ones"],
    "B": ["ladder_n4_M2_r0", "ladder_n4_M2_r1", "ladder_n4_M2_r2", "ladder_n4_M2_r3", "ladder_n4_M2_r4",
          "echo_n4_M2_r2", "readout_n4_zeros", "readout_n4_ones"],
    "C": ["ladder_n5_M4_r0", "ladder_n5_M4_r1", "ladder_n5_M4_r2", "ladder_n5_M4_r3", "ladder_n5_M4_r4",
          "echo_n5_M4_r2", "readout_n5_zeros", "readout_n5_ones"],
}
TIERS = ["A", "B", "C"]
RUNS = 3
SEED_BASE = 20261120301  # distinct from Run 1/2/4 seed bases


def schedule_for() -> dict:
    sched = {}
    for tier in TIERS:
        for run in range(1, RUNS + 1):
            rng = np.random.default_rng(SEED_BASE + hash(tier) % 1000 + run)
            sched[f"{tier}_run_{run}"] = list(rng.permutation(TIER_LABELS[tier]))
    return sched


def main() -> None:
    if OUT.exists():
        print(f"cpc_run3: already adopted at {OUT}, skipping")
        return
    if not LAYOUT_COMPARISON.exists():
        raise SystemExit("run analysis/prepare_run3.py first (layout comparison not found)")
    layout_check = json.loads(LAYOUT_COMPARISON.read_text(encoding="utf-8"))
    if layout_check["mismatches"]:
        raise SystemExit("prepare_run3.py found mismatches; refusing to adopt")
    qpy_index = json.loads(QPY_INDEX.read_text(encoding="utf-8")) if QPY_INDEX.exists() else {}

    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    run1_draft = json.loads((ROOT / "review" / "preregistration" / "cpc_run1_manifest_DRAFT.json")
                            .read_text(encoding="utf-8"))
    predictions = run1_draft["predictions_fakemarrakesh"]

    layouts = {t: layout_check["results"][t]["layout_order"] for t in TIERS}
    preregistration = {
        "status": "ADOPTED - no job submitted at the time of writing",
        "backend": "ibm_marrakesh (live calibration)",
        "transpile": {"optimization_level": 3, "seed_transpiler": 42, "dd_sequence": "XpXm"},
        "layout": {
            "method": "initial_layout PINNED per tier to Run 1's recorded physical qubits "
                      "(the modal layout across Run 1's 5 repeats, since Run 1 itself used 2-3 "
                      "distinct layouts across its own repeats) -- NOT a reuse of Run 1's saved "
                      "transpiled circuits, because Run 1's transpiled circuits were never saved "
                      "to QPY. The virtual-to-physical qubit ORDER within that set was resolved by "
                      "searching permutations for one reproducing Run 1's recorded two-qubit gate "
                      "count exactly (see run3_layout_comparison.json).",
            "deviation_from_addendum": True,
            "reference_run1_job_per_tier": layout_check["reference_job_per_tier"],
            "pinned_layout_order": layouts,
            "comparison_file": "results/cpc_revision/run3_layout_comparison.json",
        },
        "tiers": TIERS,
        "repeats_per_tier": RUNS,
        "design": {"order": {"schedule": schedule_for()}},
        "addendum": "review/OPERATING_POINT_ADDENDUM_V3.md",
        "draft_source": "review/preregistration/cpc_run3_manifest_DRAFT.json",
        "qpy_index": qpy_index,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_campaign_manifest(
        str(OUT),
        predictions=predictions,
        note=draft["note"].replace("DRAFT.", "ADOPTED."),
        max_jobs=draft["max_jobs"],
        shots=draft["shots"],
        preregistration=preregistration,
        usage_budget_seconds=draft["usage_budget_seconds"],
        max_job_seconds=draft["max_job_seconds"],
    )
    print(f"cpc_run3: adopted -> {OUT}")


if __name__ == "__main__":
    main()
