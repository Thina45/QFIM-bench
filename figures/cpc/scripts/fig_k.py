"""Fig. K: campaign timeline, broken x-axis -- panel (a) 2026-10-08 (original campaigns), panel
(b) 2026-11-19 to 2026-11-20 (Runs 1-4), both with hour-level ticks (IST). One swimlane per
campaign; each tick is a job, placed at that job's recorded CREATION/SUBMISSION time
(results/cpc_revision/job_creation_times.json -- read-only QiskitRuntimeService.job().creation_date
query, not calibration_timestamp, which precedes submission and would misplace every job before
its own preregistration commit). Preregistration commits (git log, read-only) are vertical dotted
lines in panel (b); calibration-window boundaries (manifests' calibration_timestamp, read-only,
exact moments only -- no assumed window duration) are thin shaded reference lines in both panels.

    python figures/cpc/scripts/fig_k.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in  # noqa: E402

CAMPAIGNS = [
    ("ladder_v2 (Tier A)", "ladder_v2", "campaigns/ladder_v2/manifest.json"),
    ("ladder_v2b (Tier B/C)", "ladder_v2b", "campaigns/ladder_v2b/manifest.json"),
    ("Run 1 (cpc_run1)", "cpc_run1", "campaigns/cpc_run1/manifest.json"),
    ("Run 2 (cpc_run2, DD off)", "cpc_run2", "campaigns/cpc_run2/manifest.json"),
    ("Run 4 (cpc_run4, kingston)", "cpc_run4", "campaigns/cpc_run4/manifest.json"),
    ("Run 3 (cpc_run3)", "cpc_run3", "campaigns/cpc_run3/manifest.json"),
]
PREREG_COMMITS = [
    ("494632b", "2026-11-19 14:46:33", "addendum V3 committed + pushed"),
]
DAY1_RANGE = (datetime(2026, 10, 8, 16, 0), datetime(2026, 10, 8, 20, 0))
DAY2_RANGE = (datetime(2026, 11, 19, 14, 0), datetime(2026, 11, 20, 19, 30))


def parse(ts: str) -> datetime:
    """Parse as a NAIVE datetime holding the raw IST wall-clock value (strip any UTC offset and
    fractional seconds) -- matplotlib's date axis silently converts tz-aware datetimes to UTC
    internally, which would shift every +05:30 timestamp back by 5h30m relative to the naive
    axis range/commit times used elsewhere in this script. Every timestamp in this figure must
    go through this same function so they stay on one consistent (naive, IST-valued) axis."""
    ts = ts.split("+")[0].split(".")[0].strip()
    return datetime.fromisoformat(ts.replace(" ", "T"))


def main():
    created = json.loads((ROOT / "results/cpc_revision/job_creation_times.json").read_text())
    rows = list(reversed(CAMPAIGNS))

    # correctness check: every Run 1-4 job created after the V3 commit
    v3_time = parse(PREREG_COMMITS[0][1])
    violations = []
    for _, key, _ in CAMPAIGNS:
        if key.startswith("cpc_run"):
            for r in created[key]:
                t = parse(r["created"])
                if t <= v3_time:
                    violations.append((key, r["label"], r["created"]))
    if violations:
        raise SystemExit(f"STOP: jobs created at/before the V3 commit: {violations}")
    print("checked: every Run 1-4 job was created after 494632b (2026-11-19 14:46:33 IST) -- OK")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=mm2in(190, 85), sharey=True,
                                    gridspec_kw={"width_ratios": [1, 2.2], "wspace": 0.08})

    for i, (label, key, path) in enumerate(rows):
        manifest = json.loads((ROOT / path).read_text(encoding="utf-8"))
        cal_times = sorted({parse(j["calibration_timestamp"]) for j in manifest["jobs"]
                             if j.get("calibration_timestamp")})
        times = [parse(r["created"]) for r in created[key]]
        for ax in (ax1, ax2):
            ax.plot(times, [i] * len(times), "|", color="#0072B2", markersize=10, markeredgewidth=1.4,
                    zorder=3)
            for ct in cal_times:
                ax.axvline(ct, color="#009E73", alpha=0.25, linewidth=3, zorder=1)
        ax1.text(DAY1_RANGE[0], i, label, ha="right", va="center", fontsize=6.8,
                  transform=ax1.transData)

    for hash_, date_, lab in PREREG_COMMITS:
        t = parse(date_)
        ax2.axvline(t, color="0.5", linestyle=":", linewidth=1.0, zorder=2)
        ax2.annotate(f"{hash_}  {lab}", xy=(t, len(rows) - 0.3), xytext=(t, len(rows) + 0.7),
                     ha="center", fontsize=6.3, arrowprops=dict(arrowstyle="-", color="0.5", linewidth=0.7))

    ax1.set_xlim(*DAY1_RANGE)
    ax2.set_xlim(*DAY2_RANGE)
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    for ax in (ax1, ax2):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.setp(ax.get_xticklabels(), rotation=40, ha="right", fontsize=6)
    ax1.set_xlabel("2026-10-08 (IST)")
    ax2.set_xlabel("2026-11-19 – 2026-11-20 (IST)")

    ax1.spines["right"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.tick_params(left=False)
    d = 0.015
    kwargs = dict(transform=ax1.transAxes, color="k", clip_on=False, linewidth=0.8)
    ax1.plot((1 - d, 1 + d), (-d, +d), **kwargs)
    ax1.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)
    kwargs.update(transform=ax2.transAxes)
    ax2.plot((-d / 2, +d / 2), (-d, +d), **kwargs)
    ax2.plot((-d / 2, +d / 2), (1 - d, 1 + d), **kwargs)

    ax1.set_ylim(-1, len(rows) + 1.6)
    ax1.set_yticks([])
    for spine in ("left", "top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)

    save_all(fig, "fig_k")


if __name__ == "__main__":
    main()
