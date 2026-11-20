"""Submit Run 3 (campaigns/cpc_run3/manifest.json), one (tier, run) job at a time.

    python analysis/run_run3.py --tier A --run 1
    python analysis/run_run3.py --all
    add --dry-run to transpile and report without submitting

initial_layout is pinned per tier from the manifest's preregistration.layout.pinned_layout_order
(set by analysis/adopt_run3.py from analysis/prepare_run3.py's permutation search). Every submitted
circuit is saved to QPY under campaigns/cpc_run3/qpy/ with its SHA-256 recorded in the manifest.
Refuses unless the manifest exists and verify_manifest_hash() passes. Skips a (tier, run) already
recorded. HardwareBackend itself refuses once the manifest's usage budget or job cap is reached, or
a single job bills at/over max_job_seconds.

Results: results/hardware/cpc_run3/{tier}_run{N}.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ladder_campaign import circuit_for  # noqa: E402

from qfim_bench.backends import HardwareBackend, verify_manifest_hash  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "campaigns" / "cpc_run3" / "manifest.json"
OUT_DIR = ROOT / "results" / "hardware" / "cpc_run3"
QPY_DIR = ROOT / "campaigns" / "cpc_run3" / "qpy"
TIERS = ["A", "B", "C"]
RUNS = 3


def run_one(tier: str, run: int, dry: bool) -> float | None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not verify_manifest_hash(manifest):
        raise SystemExit("cpc_run3: manifest hash does not verify; refusing")

    label = f"{tier}_run{run}"
    if not dry and any(j["label"] == label for j in manifest["jobs"]):
        print(f"cpc_run3 {label}: already run, skipping")
        return None

    order = manifest["preregistration"]["design"]["order"]["schedule"][f"{tier}_run_{run}"]
    layout = manifest["preregistration"]["layout"]["pinned_layout_order"][tier]
    hb = HardwareBackend(
        backend_name="ibm_marrakesh",
        manifest_path=str(MANIFEST),
        dry_run=dry,
        dd_sequence="XpXm",
        dd_enabled=True,
        initial_layout=layout,
        qpy_dir=None if dry else str(QPY_DIR),
    )
    hb.label = label
    results = hb.run_batch([circuit_for(c) for c in order], 8192, labels=order)
    if dry:
        print(f"cpc_run3 {label}", [c["two_qubit_gates"] for c in hb.last_report["circuits"]])
        return None

    job = json.loads(MANIFEST.read_text(encoding="utf-8"))["jobs"][-1]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{tier}_run{run}.json").write_text(json.dumps(
        {"label": label, "job": job, "order": order, "counts": {c: r.counts for c, r in zip(order, results)}},
        indent=2), encoding="utf-8")
    used = hb.cumulative_usage_seconds()
    print(f"saved cpc_run3 {label}; billed {job.get('usage_seconds')} s; cumulative {used:.1f} s of "
          f"{manifest['usage_budget_seconds']:.1f} s", flush=True)
    return job.get("usage_seconds")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--tier")
    ap.add_argument("--run", type=int, choices=range(1, RUNS + 1))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    limit = float(json.loads(MANIFEST.read_text(encoding="utf-8"))["max_job_seconds"])

    if args.all:
        plan = [(t, r) for t in TIERS for r in range(1, RUNS + 1)]
    else:
        if args.tier not in TIERS or args.run is None:
            raise SystemExit(f"--tier must be one of {TIERS} and needs --run")
        plan = [(args.tier, args.run)]

    for tier, run in plan:
        billed = run_one(tier, run, args.dry_run)
        if billed is not None and billed >= limit:
            raise SystemExit(f"job billed {billed} s, at/over the {limit} s per-job limit; stopping to re-plan")


if __name__ == "__main__":
    main()
