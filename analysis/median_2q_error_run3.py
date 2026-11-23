"""Median two-qubit gate error for Run 3, on the qubit PAIRS (edges) actually used by its
gate-bearing circuits, from the exact calibration snapshot at Run 3's own recorded
calibration_timestamp (read-only backend.properties(datetime=...) query; no job submitted) --
same method as results/cpc_revision/run1_run4_median_2q_error.json for Run 1/Run 4. Used for item
3 (effective-error ratio, 4 sessions) of the CPC v4 pass.

    python analysis/median_2q_error_run3.py
"""
import json
import os
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit_ibm_runtime import QiskitRuntimeService

ROOT = Path(__file__).resolve().parents[1]
QPY_DIR = ROOT / "campaigns" / "cpc_run3" / "qpy"
OUT = ROOT / "results" / "cpc_v4"
OUT.mkdir(parents=True, exist_ok=True)

# the busiest (most two-qubit-gate) circuit per tier, static (pre-submission) QPY files saved by
# analysis/prepare_run3.py -- same files, same pinned layout, used for every repeat in that tier
BUSIEST_QPY = {
    "A": "A_ladder_n3_M1_r4.qpy",
    "B": "B_ladder_n4_M2_r4.qpy",
    "C": "C_ladder_n5_M4_r4.qpy",
}
CALIBRATION_TIMESTAMP = "2026-11-20 03:39:26+05:30"


def edges_used(path: Path) -> set[tuple[int, int]]:
    with open(path, "rb") as f:
        qc = qpy.load(f)[0]
    edges = set()
    for inst in qc.data:
        if inst.operation.name in ("cz", "ecr", "cx") and len(inst.qubits) == 2:
            a = qc.find_bit(inst.qubits[0]).index
            b = qc.find_bit(inst.qubits[1]).index
            edges.add(tuple(sorted((a, b))))
    return edges


def main() -> None:
    all_edges: set[tuple[int, int]] = set()
    for tier, fname in BUSIEST_QPY.items():
        all_edges |= edges_used(QPY_DIR / fname)
    print("edges used (all tiers):", sorted(all_edges), "count:", len(all_edges))

    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=os.environ["IBM_QUANTUM_TOKEN"])
    backend = service.backend("ibm_marrakesh")
    from datetime import datetime, timedelta
    ts = datetime.fromisoformat(CALIBRATION_TIMESTAMP)
    # IBM's historical-properties API has an indexing lag (same issue found and offset in the
    # original historical_calibration.json pass): querying the exact target timestamp returns the
    # PREVIOUS snapshot; +8 minutes was confirmed (binary search) to land on the exact match.
    props = backend.properties(datetime=ts + timedelta(minutes=8))
    exact = str(props.last_update_date) == CALIBRATION_TIMESTAMP
    print("exact calibration match:", exact, "retrieved:", props.last_update_date)

    errors = []
    for a, b in all_edges:
        g = next((g for g in props.gates if set(g.qubits) == {a, b}), None)
        if g is None:
            continue
        err = next((p.value for p in g.parameters if p.name == "gate_error"), None)
        if err is not None:
            errors.append(err)
    median_err = float(np.median(errors))
    print("n edges with error found:", len(errors), "median error:", median_err)

    out = {"calibration_timestamp": CALIBRATION_TIMESTAMP, "exact_match": exact,
           "n_edges": len(errors), "median_two_qubit_error": median_err}
    (OUT / "run3_median_2q_error.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
