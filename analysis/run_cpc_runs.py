"""Run the CPC-revision campaigns (campaigns/cpc_run{1,2,4}/manifest.json), one job at a time.

    python analysis/run_cpc_runs.py --campaign cpc_run1 --tier A --run 1
    python analysis/run_cpc_runs.py --campaign cpc_run1 --all
    add --dry-run to transpile and report without submitting

Refuses unless the manifest exists and verify_manifest_hash() passes. Skips a (tier, run) already
recorded. HardwareBackend itself refuses once the manifest's usage budget or job cap is reached, or
a single job bills at/over max_job_seconds. Transpiles each circuit ONCE per (tier, run) call and
reuses it for that one job's 8 circuits -- repeats across --run values each get their own transpile
call against that moment's live calibration, matching how ladder_v2/v2b ran (one transpile per job,
not shared across jobs), since the point of a repeat is a fresh look at the device, not a cached
circuit object.

Results: results/hardware/cpc_run{1,2,4}/{tier}_run{N}.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ladder_campaign import circuit_for  # noqa: E402

from qfim_bench.backends import HardwareBackend, verify_manifest_hash  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

CAMPAIGNS = {
    "cpc_run1": {"backend": "ibm_marrakesh", "dd_sequence": "XpXm", "dd_enabled": True, "tiers": ["A", "B", "C"]},
    "cpc_run2": {"backend": "ibm_marrakesh", "dd_sequence": "NONE", "dd_enabled": False, "tiers": ["B"]},
    "cpc_run4": {"backend": "ibm_kingston", "dd_sequence": "XpXm", "dd_enabled": True, "tiers": ["A", "B", "C"]},
}
RUNS = 5


def run_one(campaign: str, tier: str, run: int, dry: bool) -> float | None:
    cfg = CAMPAIGNS[campaign]
    manifest_path = ROOT / "campaigns" / campaign / "manifest.json"
    out_dir = ROOT / "results" / "hardware" / campaign
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not verify_manifest_hash(manifest):
        raise SystemExit(f"{campaign}: manifest hash does not verify; refusing")

    label = f"{tier}_run{run}"
    if not dry and any(j["label"] == label for j in manifest["jobs"]):
        print(f"{campaign} {label}: already run, skipping")
        return None

    order = manifest["preregistration"]["design"]["order"]["schedule"][f"{tier}_run_{run}"]
    hb = HardwareBackend(
        backend_name=cfg["backend"],
        manifest_path=str(manifest_path),
        dry_run=dry,
        dd_sequence=cfg["dd_sequence"],
        dd_enabled=cfg["dd_enabled"],
    )
    hb.label = label
    results = hb.run_batch([circuit_for(c) for c in order], 8192, labels=order)
    if dry:
        print(f"{campaign} {label}", [c["two_qubit_gates"] for c in hb.last_report["circuits"]])
        return None

    job = json.loads(manifest_path.read_text(encoding="utf-8"))["jobs"][-1]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tier}_run{run}.json").write_text(json.dumps(
        {"label": label, "job": job, "order": order, "counts": {c: r.counts for c, r in zip(order, results)}},
        indent=2), encoding="utf-8")
    used = hb.cumulative_usage_seconds()
    print(f"saved {campaign} {label}; billed {job.get('usage_seconds')} s; cumulative {used:.1f} s of "
          f"{manifest['usage_budget_seconds']:.1f} s", flush=True)
    return job.get("usage_seconds")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True, choices=list(CAMPAIGNS))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--tier")
    ap.add_argument("--run", type=int, choices=range(1, RUNS + 1))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = CAMPAIGNS[args.campaign]
    manifest_path = ROOT / "campaigns" / args.campaign / "manifest.json"
    limit = float(json.loads(manifest_path.read_text(encoding="utf-8"))["max_job_seconds"])

    if args.all:
        plan = [(t, r) for t in cfg["tiers"] for r in range(1, RUNS + 1)]
    else:
        if args.tier not in cfg["tiers"] or args.run is None:
            raise SystemExit(f"--tier must be one of {cfg['tiers']} and needs --run")
        plan = [(args.tier, args.run)]

    for tier, run in plan:
        billed = run_one(args.campaign, tier, run, args.dry_run)
        if billed is not None and billed >= limit:
            raise SystemExit(f"job billed {billed} s, at/over the {limit} s per-job limit; stopping to re-plan")


if __name__ == "__main__":
    main()
