"""Run Tiers B and C (campaigns/ladder_v2b/manifest.json).

    python analysis/run_ladder_campaign_bc.py --all             # every remaining run: all of B, then all of C
    python analysis/run_ladder_campaign_bc.py --tier B --run 1  # a single run
    add --dry-run to transpile and report without submitting

Refuses unless the manifest SHA-256 verifies and equals PINNED_HASH. Skips runs already recorded,
runs tier C only after all five B runs exist, stops at the first job that bills more than the
per-job limit or fails, and HardwareBackend itself refuses once the manifest's usage budget or job
cap is reached. Results: results/hardware/ladder_v2b/{tier}_run{N}.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ladder_campaign import circuit_for  # noqa: E402

from qfim_bench.backends import HardwareBackend, verify_manifest_hash  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "campaigns" / "ladder_v2b" / "manifest.json"
OUT = ROOT / "results" / "hardware" / "ladder_v2b"
PINNED_HASH = "ac2958ceca952f82955ad6e5bbc67b9327aa046e85691a3dfee36a685828c145"
RUNS = 5


def run_one(tier: str, run: int, dry: bool) -> float | None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    label = f"tier{tier}_run{run}"
    if not dry and any(j["label"] == label for j in manifest["jobs"]):
        print(f"{label}: already run, skipping")
        return None
    order = manifest["preregistration"]["design"]["order"]["schedule"][f"{tier}_run_{run}"]
    hb = HardwareBackend(manifest_path=str(MANIFEST), dry_run=dry)
    hb.label = label
    results = hb.run_batch([circuit_for(c) for c in order], 8192, labels=order)
    if dry:
        print(label, [c["two_qubit_gates"] for c in hb.last_report["circuits"]])
        return None
    job = json.loads(MANIFEST.read_text(encoding="utf-8"))["jobs"][-1]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tier}_run{run}.json").write_text(json.dumps(
        {"label": label, "job": job, "order": order, "counts": {c: r.counts for c, r in zip(order, results)}},
        indent=2), encoding="utf-8")
    used = hb.cumulative_usage_seconds()
    print(f"saved {label}; billed {job.get('usage_seconds')} s; cumulative {used:.0f} s of "
          f"{manifest['usage_budget_seconds']:.0f} s", flush=True)
    return job.get("usage_seconds")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--tier", choices=["B", "C"])
    ap.add_argument("--run", type=int, choices=range(1, RUNS + 1))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not verify_manifest_hash(manifest) or manifest["sha256"] != PINNED_HASH:
        raise SystemExit("manifest hash does not verify or does not match the pinned hash; refusing")
    limit = float(manifest["max_job_seconds"])

    plan = [(t, r) for t in "BC" for r in range(1, RUNS + 1)] if args.all else [(args.tier, args.run)]
    if not args.all and args.run is None:
        raise SystemExit("--tier needs --run")
    for tier, run in plan:
        if tier == "C" and not args.dry_run:
            done_b = {j["label"] for j in json.loads(MANIFEST.read_text(encoding="utf-8"))["jobs"]}
            if not all(f"tierB_run{r}" in done_b for r in range(1, RUNS + 1)):
                raise SystemExit("finish all five tier B runs before tier C")
        billed = run_one(tier, run, args.dry_run)
        if billed is not None and billed >= limit:
            raise SystemExit(f"job billed {billed} s, at/over the {limit} s per-job limit; stopping to re-plan")


if __name__ == "__main__":
    main()
