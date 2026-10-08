"""Phase 2D: is the repeat-based TVD interval calibrated? (simulated data with known truth)

32 outcomes, 8192 shots, 5 repeats. The "truth" distribution is uniform; the reference q is uniform
tilted so that TVD(p_true, q) takes the values 0, 0.01, 0.02, 0.05, 0.10, 0.20. For each, the
interval qfim-bench's tvd_with_uncertainty reports (a t-interval over 5 repeated empirical TVDs) is
checked for how often it contains the true TVD, and so is the same interval shifted down by the
null floor. Also recorded: the null floors and the p-value behaviour under the null.

    python analysis/tvd_calibration.py
"""

import json
from pathlib import Path

import numpy as np

from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.tvd_calibration import null_floor, tvd, tvd_ci_coverage, tvd_pvalue, two_sample_tvd_pvalue

OUT = Path(__file__).resolve().parents[1] / "results" / "sim"
P = np.full(32, 1 / 32)


def tilted(target_tvd: float) -> np.ndarray:
    """q with TVD(P, q) == target: move mass target from the second half of outcomes to the first."""
    q = P.copy()
    q[:16] += target_tvd / 16
    q[16:] -= target_tvd / 16
    return q


def main() -> None:
    rows = []
    for target in (0.0, 0.01, 0.02, 0.05, 0.10, 0.20):
        q = tilted(target)
        assert abs(tvd(P, q) - target) < 1e-12
        cov = tvd_ci_coverage(P, q, shots=8192, repeats=5, sims=1000, seed=7)
        rows.append(cov)
        print(f"true TVD {cov['true_tvd']:.3f}: naive coverage {cov['coverage_naive']:.3f}, "
              f"floor-corrected {cov['coverage_floor_corrected']:.3f} (nominal 0.95)")
    rng = np.random.default_rng(3)
    one = rng.multinomial(8192, P)
    two = rng.multinomial(8192, P)
    summary = {
        "coverage": rows,
        "null_floor_vs_truth": null_floor(P, 8192, draws=5000, seed=1),
        "null_floor_two_runs": two_sample_tvd_pvalue(one, two, draws=1000, seed=2)["null_floor"],
        "example_pvalue_same_distribution": tvd_pvalue(one, P, draws=5000, seed=1),
    }
    print("null floors:", summary["null_floor_vs_truth"], summary["null_floor_two_runs"])
    (OUT / "tvd_calibration.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_experiment_manifest(str(OUT / "tvd_calibration_manifest.json"), {"script": "analysis/tvd_calibration.py"}, overwrite=True)


if __name__ == "__main__":
    main()
