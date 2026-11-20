"""Fig. K: campaign timeline, 2026-10-08 to 2026-11-20. One swimlane per campaign; a tick per job,
placed at that job's recorded calibration_timestamp (campaigns/<name>/manifest.json -- no live API
query, read-only from the saved manifests). Preregistration commits are marked with their short
hash and date (git log, read-only). "addendum V3 committed and pushed" is annotated explicitly,
before any Run 1 tick. Data from git log and the manifests only -- no new computation.

    python figures/cpc/scripts/fig_k.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in  # noqa: E402

# campaign -> (row label, manifest path)
CAMPAIGNS = [
    ("ladder_v2 (Tier A)", "campaigns/ladder_v2/manifest.json"),
    ("ladder_v2b (Tier B/C)", "campaigns/ladder_v2b/manifest.json"),
    ("Run 1 (cpc_run1)", "campaigns/cpc_run1/manifest.json"),
    ("Run 2 (cpc_run2, DD off)", "campaigns/cpc_run2/manifest.json"),
    ("Run 4 (cpc_run4, kingston)", "campaigns/cpc_run4/manifest.json"),
    ("Run 3 (cpc_run3)", "campaigns/cpc_run3/manifest.json"),
]

# (short hash, date, label) -- from `git log --format="%h|%ad|%s" --date=iso-local`, read-only
PREREG_COMMITS = [
    ("c25b1b0 / dd01e6e", "2026-10-08 16:30", "operating-point criterion + addendum (DRAFT)"),
    ("494632b", "2026-11-19 14:46", "addendum V3 committed + pushed"),
]


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace(" ", "T"))


def main():
    fig, ax = plt.subplots(figsize=mm2in(190, 85))

    rows = list(reversed(CAMPAIGNS))
    for i, (label, path) in enumerate(rows):
        manifest = json.loads((ROOT / path).read_text(encoding="utf-8"))
        times = [parse(j["calibration_timestamp"]) for j in manifest["jobs"] if j.get("calibration_timestamp")]
        ax.plot(times, [i] * len(times), "|", color="#0072B2", markersize=10, markeredgewidth=1.4)
        ax.text(mdates.date2num(datetime(2026, 10, 7, 12)), i, label, ha="right", va="center", fontsize=6.8)

    level_y = [len(rows) + 0.6, len(rows) + 0.6]
    for (hash_, date_, label), ly in zip(PREREG_COMMITS, level_y):
        t = parse(date_)
        ax.axvline(t, color="0.75", linestyle=":", linewidth=0.8, zorder=0)
        ax.annotate(f"{hash_}  {label}", xy=(t, len(rows) - 0.3), xytext=(t, ly),
                    ha="center", fontsize=6.3, rotation=0,
                    arrowprops=dict(arrowstyle="-", color="0.5", linewidth=0.7))

    ax.set_ylim(-1, len(rows) + 1.8)
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=4))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    ax.set_xlabel("date")
    for spine in ("left", "top", "right"):
        ax.spines[spine].set_visible(False)

    save_all(fig, "fig_k")


if __name__ == "__main__":
    main()
