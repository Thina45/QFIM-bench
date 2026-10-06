"""Quickstart: run the full pipeline on the bundled sample dataset with no credentials.

    python examples/quickstart.py

By default this uses the uniform start state (H^{\\otimes n}|0>), which is
the regime Eq. (4)'s theoretical success-probability formula assumes. On
the noiseless Aer simulator this run reproduces that theoretical curve
almost exactly (sampling noise only). To instead reproduce the companion
paper's actual hardware circuit (a random EfficientSU2 ansatz start, flat
even without noise), pass initial_state="ansatz" below — see the
README's "Start state" section before doing that.
"""

from pathlib import Path

from qfim_bench.classical import brute_force_frequent_itemsets
from qfim_bench.config import QFIMConfig
from qfim_bench.pipeline import run_qfim_bench
from qfim_bench.preprocessing import load_transactions, reduce_to_selected_items, select_top_k_items

DATA = Path(__file__).resolve().parents[1] / "data" / "sample_transactions.csv"


def main() -> None:
    cfg = QFIMConfig(
        dataset_path=str(DATA),
        top_k_items=5,
        oracle_threshold=2,
        grover_iterations=2,
        shots=8192,
        initial_state="uniform",  # Eq. (4) regime — the package's verified, reproducible claim
        seed=42,
    )

    transactions = load_transactions(cfg.dataset_path)
    order = select_top_k_items(transactions, cfg.top_k_items)
    reduced = reduce_to_selected_items(transactions, order)
    truth = set(brute_force_frequent_itemsets(reduced, cfg.min_support))

    result = run_qfim_bench(cfg, ground_truth_frequent=truth, manifest_path="results/quickstart_run/manifest.json")

    print(f"items:              {order}")
    print(f"M, N, theta:        {result.circuit_info.M}, {result.circuit_info.N}, {result.circuit_info.theta:.4f}")
    print(f"theoretical P(r):   {result.circuit_info.theoretical_p:.4f}")
    marked = sum(c for b, c in result.execution.counts.items() if b.count("1") >= cfg.oracle_threshold)
    print(f"empirical P(marked): {marked / cfg.shots:.4f}  (should track theoretical P(r) closely; uniform start)")
    print(f"ground-truth size:  {len(truth)}")
    print(f"precision/recall/F1: {result.metrics.precision:.4f} / {result.metrics.recall:.4f} / {result.metrics.f1:.4f}")


if __name__ == "__main__":
    main()
