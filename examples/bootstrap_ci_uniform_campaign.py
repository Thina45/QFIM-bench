"""
examples/bootstrap_ci_uniform_campaign.py — computes a bootstrap CI for
each hardware run's empirical success probability, turning the five point
estimates into numbers with real uncertainty for the manuscript table.

Run from the qfim-bench root:
    PYTHONPATH=src python examples/bootstrap_ci_uniform_campaign.py
"""

import json
from pathlib import Path

from qfim_bench.statistics import bootstrap_ci

CAMPAIGN = Path(__file__).resolve().parents[1] / "campaigns" / "uniform_marrakesh"


def per_shot_outcomes(counts: dict[str, int]) -> list[float]:
    """Expand a counts dict into a flat list of 0/1 outcomes (1 = marked, Hamming weight >= 2)."""
    outcomes = []
    for bitstring, c in counts.items():
        marked = 1.0 if bitstring.count("1") >= 2 else 0.0
        outcomes.extend([marked] * c)
    return outcomes


def main() -> None:
    for label, fname in [("r=1", "r1"), ("r=2", "r2"), ("r=2 (repeat)", "r2_repeat"),
                          ("r=3", "r3"), ("r=4", "r4")]:
        f = CAMPAIGN / f"{fname}.json"
        if not f.exists():
            print(f"{label}: no data at {f}, skipping")
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        outcomes = per_shot_outcomes(d["counts"])
        point = sum(outcomes) / len(outcomes)
        lo, hi = bootstrap_ci(outcomes, confidence_level=0.95, n_resamples=2000, seed=42)
        print(f"{label}: p={point:.4f}  95% CI [{lo:.4f}, {hi:.4f}]  "
              f"theory={d['theoretical_p']:.5f}")


if __name__ == "__main__":
    main()
