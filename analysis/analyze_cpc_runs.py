"""Analyse the CPC-revision hardware runs (campaigns/cpc_run1, cpc_run2, cpc_run4) and compare
against the original campaigns/ladder_v2 + ladder_v2b data (Oct 8, 2026). Reuses the exact
per-cell mean/t-interval method of analysis/analyze_ladder_tierA.py (5 jobs, 4 d.f. t-interval
across the daily/repeat values), applied generically to any 5-run result directory.

    python analysis/analyze_cpc_runs.py
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
T975_DF4 = 2.7764451051977987
PRED = {c["id"]: c for c in json.loads((ROOT / "review/preregistration/ladder_predictions.json").read_text())["circuits"]}
LADDER_B_MARKED = [i for i in range(16) if bin(i).count("1") == 2][:2]
LADDER_C_MARKED = [i for i in range(32) if bin(i).count("1") == 2][:4]


def marked_keys(cid: str) -> set:
    n = int(cid.split("_")[1][1:])
    if cid.startswith("ladder_n3"):
        return {format(i, f"0{n}b") for i in PRED[cid]["marked"]}
    if cid.startswith("echo"):
        return {"0" * n}
    if cid.startswith("readout"):
        return {("1" if cid.endswith("ones") else "0") * n}
    if cid.startswith("ladder_n4"):
        return {format(i, f"0{n}b") for i in LADDER_B_MARKED}
    if cid.startswith("ladder_n5"):
        return {format(i, f"0{n}b") for i in LADDER_C_MARKED}
    raise ValueError(cid)


def load_runs(out_dir: Path, tier_prefix: str, n_runs: int = 5) -> list[dict]:
    return [json.loads((out_dir / f"{tier_prefix}_run{i}.json").read_text(encoding="utf-8")) for i in range(1, n_runs + 1)]


def cell_stats(runs: list[dict], cid: str) -> dict:
    vals, tot_k, tot_n = [], 0, 0
    keys = marked_keys(cid)
    gates = []
    for run in runs:
        c = run["counts"][cid]
        k, tn = sum(x for key, x in c.items() if key in keys), sum(c.values())
        vals.append(k / tn); tot_k += k; tot_n += tn
        info = next(i for i, lbl in zip(run["job"]["circuits_info"], run["job"]["labels"]) if lbl == cid)
        gates.append(info["two_qubit_gates"])
    mean, sd = float(np.mean(vals)), float(np.std(vals, ddof=1))
    half = T975_DF4 * sd / math.sqrt(len(vals))
    return {"id": cid, "daily": vals, "mean": mean, "sd": sd, "t_ci95": [mean - half, mean + half],
            "two_qubit_gates": float(np.mean(gates)), "n_runs": len(vals)}


def main() -> None:
    cells_by_tier = {
        "A": [f"ladder_n3_M1_r{r}" for r in range(5)] + ["echo_n3_M1_r2", "readout_n3_zeros", "readout_n3_ones"],
        "B": [f"ladder_n4_M2_r{r}" for r in range(5)] + ["echo_n4_M2_r2", "readout_n4_zeros", "readout_n4_ones"],
        "C": [f"ladder_n5_M4_r{r}" for r in range(5)] + ["echo_n5_M4_r2", "readout_n5_zeros", "readout_n5_ones"],
    }

    results = {}
    for campaign, tiers in [("cpc_run1", ["A", "B", "C"]), ("cpc_run2", ["B"]), ("cpc_run4", ["A", "B", "C"])]:
        out_dir = ROOT / "results" / "hardware" / campaign
        results[campaign] = {}
        for tier in tiers:
            runs = load_runs(out_dir, tier)
            results[campaign][tier] = {cid: cell_stats(runs, cid) for cid in cells_by_tier[tier]}

    (ROOT / "results" / "cpc_revision" / "cpc_runs_analysis.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    for camp, tiers in results.items():
        for tier, cells in tiers.items():
            for cid, s in cells.items():
                print(f"{camp:10s} {tier} {cid:20s} mean={s['mean']:.4f} CI=[{s['t_ci95'][0]:.4f},{s['t_ci95'][1]:.4f}]")


if __name__ == "__main__":
    main()
