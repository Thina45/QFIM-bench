"""EXPLORATORY: ladder_v2b Tier C runs 1-3 (calibration 2026-10-08 18:13:43+05:30) vs runs 4-5
(calibration 2026-10-08 18:32:55+05:30). Not preregistered; the split was discovered in Phase 0, not
planned in advance. n=2 and n=3 subgroups are both too small for a reliable t-interval -- both are
reported, with the small-n caveat stated explicitly rather than implied by a number alone.

    python analysis/phase1_exploratory_tierC_calibration_split.py
"""

import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HWB = ROOT / "results" / "hardware" / "ladder_v2b"
OUT = ROOT / "results" / "cpc_revision"

PREDICTIONS = {
    c["id"]: c
    for c in json.loads((ROOT / "review" / "preregistration" / "ladder_predictions.json").read_text())["circuits"]
}

GROUP_1_3 = [1, 2, 3]  # calibration 18:13:43+05:30
GROUP_4_5 = [4, 5]     # calibration 18:32:55+05:30


def marked_bitstrings(cid: str, n: int) -> set[str]:
    return {format(i, f"0{n}b") for i in PREDICTIONS[cid]["marked"]}


def run_fraction(run_idx: int, cid: str, n: int, marked: set[str]) -> float:
    d = json.loads((HWB / f"C_run{run_idx}.json").read_text(encoding="utf-8"))
    c = d["counts"][cid]
    k = sum(x for key, x in c.items() if key in marked)
    t = sum(c.values())
    return k / t


def subgroup_stats(vals: list[float]) -> dict:
    mean = float(np.mean(vals))
    if len(vals) > 1:
        sd = float(np.std(vals, ddof=1))
        se = sd / math.sqrt(len(vals))
    else:
        sd, se = float("nan"), float("nan")
    return {"mean": mean, "sd": sd, "se": se, "n_runs": len(vals), "values": vals}


def main() -> None:
    n = 5
    ids = ["ladder_n5_M4_r0", "ladder_n5_M4_r1", "ladder_n5_M4_r2", "ladder_n5_M4_r3",
           "ladder_n5_M4_r4", "echo_n5_M4_r2", "readout_n5_zeros", "readout_n5_ones"]
    rows = []
    for cid in ids:
        if cid.startswith("readout"):
            marked = {("1" if cid.endswith("ones") else "0") * n}
        elif cid.startswith("echo"):
            marked = {"0" * n}  # echo target: all-zeros return probability
        else:
            marked = marked_bitstrings(cid, n)
        vals_1_3 = [run_fraction(i, cid, n, marked) for i in GROUP_1_3]
        vals_4_5 = [run_fraction(i, cid, n, marked) for i in GROUP_4_5]
        s1, s2 = subgroup_stats(vals_1_3), subgroup_stats(vals_4_5)
        diff = s2["mean"] - s1["mean"]
        # Width of each subgroup's own spread (max-min of its point estimates) as the "within-subgroup
        # CI width" proxy, since n=2/n=3 is too small for a trustworthy t-interval.
        width_1_3 = max(vals_1_3) - min(vals_1_3)
        width_4_5 = max(vals_4_5) - min(vals_4_5) if len(vals_4_5) > 1 else float("nan")
        exceeds_within_spread = abs(diff) > max(width_1_3, width_4_5 if not math.isnan(width_4_5) else 0.0)
        rows.append({
            "status": "EXPLORATORY",
            "circuit_id": cid,
            "calib_18_13_mean": s1["mean"], "calib_18_13_sd": s1["sd"], "calib_18_13_n_runs": s1["n_runs"],
            "calib_18_32_mean": s2["mean"], "calib_18_32_sd": s2["sd"], "calib_18_32_n_runs": s2["n_runs"],
            "diff_18_32_minus_18_13": diff,
            "within_subgroup_spread_18_13": width_1_3,
            "within_subgroup_spread_18_32": width_4_5,
            "diff_exceeds_within_subgroup_spread": exceeds_within_spread,
            "caveat": "n=3 and n=2 runs per subgroup; point estimates only, no reliable t-interval",
        })

    path = OUT / "phase1_exploratory_tierC_calibration_split.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"EXPLORATORY Tier C calibration-split comparison -> {path}")
    for r in rows:
        print(f"  {r['circuit_id']:20s} 18:13(n=3)={r['calib_18_13_mean']:.4f}  "
              f"18:32(n=2)={r['calib_18_32_mean']:.4f}  diff={r['diff_18_32_minus_18_13']:+.4f}  "
              f"exceeds_within_spread={r['diff_exceeds_within_subgroup_spread']}")


if __name__ == "__main__":
    main()
