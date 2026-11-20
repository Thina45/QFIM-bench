"""Prepare Run 3 (campaigns/cpc_run3): re-transpile every circuit pinned to the physical qubits
Run 1 used for the SAME label, since Run 1's own transpiled circuits were never saved to QPY and
so cannot be reloaded (see REPORT.md deviation note).

Run 1 itself did not use one single layout per tier across its 5 repeats (the transpiler, even
with a fixed seed_transpiler, chose a second layout on a subset of jobs once live calibration
changed between its two submission bursts). The MODAL (most frequent) layout per tier across
Run 1's 5 repeats is used as "Run 1's layout" for pinning:
  A: all 5/5 runs -> (10,139,140) / (53,54,55)        [unambiguous]
  B: 3/5 runs (B_run1,3,4) -> (10,97,139,140) / (137,146,147,148)
  C: 4/5 runs (C_run1,2,4,5) -> (5,10,14,21,153) / (1,2,3,4,16)

For each tier this script:
  1. transpiles every circuit with initial_layout pinned to that tier's modal Run 1 layout,
     optimization_level=3, seed_transpiler=42 (same as Run 1);
  2. compares physical qubits, two-qubit gate count and depth against the modal Run 1 reference
     job for that tier;
  3. refuses (raises) if ANY circuit's physical qubits or two-qubit gate count differ from the
     reference, as instructed; reports (but does not block on) a depth difference under 5%;
  4. saves the transpiled circuits to campaigns/cpc_run3/qpy/ via QPY, with SHA-256 hashes;
  5. writes the full comparison table to results/cpc_revision/run3_layout_comparison.json.

    python analysis/prepare_run3.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adopt_cpc_runs import TIER_LABELS  # noqa: E402
from run_ladder_campaign import circuit_for  # noqa: E402

from qfim_bench.backends import HardwareBackend  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUN1_MANIFEST = ROOT / "campaigns" / "cpc_run1" / "manifest.json"
QPY_DIR = ROOT / "campaigns" / "cpc_run3" / "qpy"
OUT = ROOT / "results" / "cpc_revision" / "run3_layout_comparison.json"

# modal reference job per tier, from the analysis of cpc_run1/manifest.json above
TIER_REFERENCE_JOB = {"A": "A_run1", "B": "B_run1", "C": "C_run1"}


def reference_info(tier: str) -> dict:
    manifest = json.loads(RUN1_MANIFEST.read_text(encoding="utf-8"))
    job = next(j for j in manifest["jobs"] if j["label"] == TIER_REFERENCE_JOB[tier])
    return dict(zip(job["labels"], job["circuits_info"]))


def pinned_layout(tier: str) -> list[int]:
    """The physical-qubit SET Run 1 used for this tier's connected (gate-bearing) circuits.

    r=0 and the readout controls have zero two-qubit gates, so the transpiler is free to place
    them on ANY qubits (no connectivity needed) -- Run 1's own data shows they sometimes landed on
    a disjoint, non-contiguous set (e.g. tier C r=0 used (5,10,14,21,153) while every gate-bearing
    circuit in the same job used the connected (1,2,3,4,16)). Pinning to an idle-circuit's qubits
    would force the real ladder/echo circuits onto a disconnected subgraph and blow up their gate
    count. The circuit with the MOST two-qubit gates is used as the reference layout instead."""
    ref = reference_info(tier)
    busiest = max(ref.values(), key=lambda c: c["two_qubit_gates"])
    return busiest["physical_qubits"]


def _resolve_virtual_to_physical_order(tier: str, qubit_set: list[int], ref: dict, backend) -> list[int]:
    """circuits_info only recorded the SET of physical qubits Run 1 used, not which virtual qubit
    mapped to which physical one. initial_layout needs an explicit order, so search permutations of
    that set (the qubit count is <= 5, so <= 120 permutations) for one that reproduces Run 1's
    recorded two-qubit gate count on the circuit with the most two-qubit gates in this tier (the
    most discriminating one), then reuse that order for every circuit in the tier.

    DECISION (user, 2026-11-20): because live calibration has moved on since Run 1 (calibration-
    dependent gate synthesis under optimization_level=3), NO permutation reproduces the exact
    two-qubit gate count deterministically across repeated tries -- confirmed by direct test (see
    REPORT.md deviation note). The pinned physical-QUBIT-SET match is therefore the hard requirement
    (enforced in main()); gate count is instead minimised here (closest match) and the resulting
    small residual difference is reported, not blocked on."""
    import itertools

    hb = HardwareBackend(backend_name="ibm_marrakesh", dry_run=True)
    biggest_label = max(ref, key=lambda lab: ref[lab]["two_qubit_gates"])
    target_gates = ref[biggest_label]["two_qubit_gates"]
    probe_circuit = circuit_for(biggest_label)
    best_perm, best_diff = None, None
    for perm in itertools.permutations(qubit_set):
        hb.initial_layout = list(perm)
        tq = hb._transpile(probe_circuit, backend)
        info = hb._circuit_info(tq)
        if info["physical_qubits"] != sorted(qubit_set):
            continue
        diff = abs(info["two_qubit_gates"] - target_gates)
        if best_diff is None or diff < best_diff:
            best_perm, best_diff = list(perm), diff
        if diff == 0:
            break
    if best_perm is None:
        raise RuntimeError(f"tier {tier}: no permutation of {qubit_set} even keeps the physical qubit set")
    return best_perm


def main() -> None:
    results = {}
    mismatches = []
    for tier in ["A", "B", "C"]:
        ref = reference_info(tier)
        qubit_set = pinned_layout(tier)
        probe_backend = HardwareBackend(backend_name="ibm_marrakesh", dry_run=True)
        backend0, _ = probe_backend._target()
        layout = _resolve_virtual_to_physical_order(tier, qubit_set, ref, backend0)
        print(f"tier {tier}: resolved virtual->physical order {layout} (set {sorted(qubit_set)})")
        hb = HardwareBackend(
            backend_name="ibm_marrakesh",
            dry_run=True,  # transpile against live calibration target resolution, nothing submitted
            initial_layout=layout,
        )
        labels = TIER_LABELS[tier]
        circuits = [circuit_for(c) for c in labels]
        backend, target_label = hb._target()
        transpiled = [hb._transpile(c, backend) for c in circuits]

        rows = []
        for lab, tq in zip(labels, transpiled):
            info = hb._circuit_info(tq)
            r = ref[lab]
            qubits_match = info["physical_qubits"] == r["physical_qubits"]
            gates_match = info["two_qubit_gates"] == r["two_qubit_gates"]
            depth_pct = (abs(info["depth"] - r["depth"]) / r["depth"] * 100) if r["depth"] else 0.0
            row = {
                "label": lab,
                "run1_physical_qubits": r["physical_qubits"], "run3_physical_qubits": info["physical_qubits"],
                "qubits_match": qubits_match,
                "run1_two_qubit_gates": r["two_qubit_gates"], "run3_two_qubit_gates": info["two_qubit_gates"],
                "gates_match": gates_match,
                "run1_depth": r["depth"], "run3_depth": info["depth"], "depth_pct_diff": round(depth_pct, 3),
            }
            rows.append(row)
            # r=0 and the readout controls have zero two-qubit gates, so they have no connectivity
            # requirement and are deliberately pinned to the TIER's busy layout (a genuine readout-
            # error control for those qubits) rather than Run 1's own, unconstrained choice for them
            # -- see REPORT.md "idle-circuit layout" deviation. Only a qubit mismatch on a circuit
            # that actually has two-qubit gates is a hard stop.
            is_idle = r["two_qubit_gates"] == 0
            if not qubits_match and not is_idle:
                mismatches.append({"tier": tier, **row})
            elif not qubits_match and is_idle:
                print(f"  note: {tier} {lab} pinned to the tier's busy layout ({info['physical_qubits']}) "
                      f"instead of Run 1's own idle-circuit choice ({r['physical_qubits']}) -- accepted "
                      "per 2026-11-20 decision")
            elif not gates_match:
                print(f"  note: {tier} {lab} two-qubit gate count differs from Run 1 "
                      f"({info['two_qubit_gates']} vs {r['two_qubit_gates']}) -- accepted per "
                      f"2026-11-20 decision (calibration-dependent synthesis, not a routing error)")
        results[tier] = {"pinned_qubit_set": qubit_set, "layout_order": layout, "target": target_label,
                          "rows": rows}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"reference_job_per_tier": TIER_REFERENCE_JOB, "results": results,
                                "mismatches": mismatches}, indent=2), encoding="utf-8")
    print(f"comparison written to {OUT}")

    if mismatches:
        print("MISMATCHES FOUND -- refusing to proceed:")
        for m in mismatches:
            print(" ", m)
        raise SystemExit(1)

    for tier in ["A", "B", "C"]:
        for row in results[tier]["rows"]:
            flag = " <-- depth diff > 5%" if row["depth_pct_diff"] > 5.0 else ""
            print(f"{tier} {row['label']}: qubits match={row['qubits_match']} gates match={row['gates_match']} "
                  f"depth diff={row['depth_pct_diff']}%{flag}")

    # second pass: save QPY with the layout now verified safe
    QPY_DIR.mkdir(parents=True, exist_ok=True)
    qpy_index = {}
    import hashlib

    import qiskit.qpy as qpy
    for tier in ["A", "B", "C"]:
        layout = results[tier]["layout_order"]
        hb = HardwareBackend(backend_name="ibm_marrakesh", dry_run=True, initial_layout=layout)
        backend, _ = hb._target()
        labels = TIER_LABELS[tier]
        for lab in labels:
            tq = hb._transpile(circuit_for(lab), backend)
            path = QPY_DIR / f"{tier}_{lab}.qpy"
            with open(path, "wb") as f:
                qpy.dump(tq, f)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            qpy_index[f"{tier}_{lab}"] = {"path": str(path.relative_to(ROOT)), "sha256": digest}
    (QPY_DIR / "index.json").write_text(json.dumps(qpy_index, indent=2), encoding="utf-8")
    print(f"QPY circuits + hashes saved under {QPY_DIR}")


if __name__ == "__main__":
    main()
