"""Run the adopted ladder campaign (campaigns/ladder_v2/manifest.json), one stage at a time.

    python analysis/run_ladder_campaign.py --probe          # one tiny job, must bill <= 10 s
    python analysis/run_ladder_campaign.py --day 1          # Tier A, one job of 8 circuits
    add --dry-run to transpile and report without submitting

Refuses to run unless the manifest's SHA-256 verifies and equals PINNED_HASH, the probe is done
(for --day), the day has not been run, and the order comes from the manifest's preregistered
schedule. Results go to results/hardware/ladder_v2/. Needs IBM_QUANTUM_TOKEN in the environment.
"""

import argparse
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ladder_predictions import echo_circuit, marked_set, readout_circuit  # noqa: E402

from qfim_bench.backends import HardwareBackend, verify_manifest_hash  # noqa: E402
from qfim_bench.circuit import build_grover_circuit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "campaigns" / "ladder_v2" / "manifest.json"
OUT = ROOT / "results" / "hardware" / "ladder_v2"
PINNED_HASH = "6dcfc075d5e4af26a786ca2ee2cc911955f0104e6fb228da5c51bdd783bef3b9"
PROBE_CAP_S = 10.0


def circuit_for(cid: str) -> QuantumCircuit:
    parts = cid.split("_")
    kind = parts[0]
    n = int(parts[1][1:])
    if kind == "ladder":
        M, r = int(parts[2][1:]), int(parts[3][1:])
        return build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked_set(n, M), oracle_style="mcz")[0]
    if kind == "echo":
        return echo_circuit(n, int(parts[2][1:]), int(parts[3][1:]))
    if kind == "readout":
        return readout_circuit(n, parts[2] == "ones")
    raise ValueError(cid)


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", action="store_true")
    g.add_argument("--day", type=int, choices=range(1, 6))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not verify_manifest_hash(manifest) or manifest["sha256"] != PINNED_HASH:
        raise SystemExit("manifest hash does not verify or does not match the pinned hash; refusing")
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = manifest.get("jobs", [])
    probe_done = any(j["label"] == "probe" for j in jobs)

    hb = HardwareBackend(manifest_path=str(MANIFEST), dry_run=args.dry_run)
    if args.probe:
        if probe_done and not args.dry_run:
            raise SystemExit("probe already run")
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)
        hb.label = "probe"
        hb.run_batch([qc], 8192, labels=["probe"])
    else:
        label = f"tierA_day{args.day}"
        if not probe_done and not args.dry_run:
            raise SystemExit("run the probe first")
        probe = next((j for j in jobs if j["label"] == "probe"), None)
        if probe and (probe.get("usage_seconds") is None or probe["usage_seconds"] > PROBE_CAP_S) and not args.dry_run:
            raise SystemExit(f"probe billed {probe.get('usage_seconds')} s (cap {PROBE_CAP_S}); stop and re-plan")
        if any(j["label"] == label for j in jobs) and not args.dry_run:
            raise SystemExit(f"{label} already run")
        order = manifest["preregistration"]["design"]["order_randomisation"]["schedule"][f"day_{args.day}"]
        hb.label = label
        results = hb.run_batch([circuit_for(c) for c in order], 8192, labels=order)
        if args.dry_run:
            print(json.dumps(hb.last_report["circuits"], indent=1))
            return
        job = json.loads(MANIFEST.read_text(encoding="utf-8"))["jobs"][-1]
        (OUT / f"day{args.day}.json").write_text(json.dumps(
            {"label": label, "job": job, "order": order,
             "counts": {cid: r.counts for cid, r in zip(order, results)}}, indent=2), encoding="utf-8")
        print(f"saved day {args.day}; billed {job.get('usage_seconds')} s")
        return
    if not args.dry_run:
        job = json.loads(MANIFEST.read_text(encoding="utf-8"))["jobs"][-1]
        (OUT / "probe.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
        print(f"probe billed {job.get('usage_seconds')} s (cap {PROBE_CAP_S})")
    else:
        print(json.dumps(hb.last_report, indent=1, default=str)[:600])


if __name__ == "__main__":
    main()
