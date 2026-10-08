"""Quickstart: Grover-based frequent itemset search on the bundled sample data, no credentials.

    python examples/quickstart.py

What this does: the set of frequent itemsets is computed classically and used to mark basis states
(the oracle's marked set is precomputed); Grover iterations amplify that set on a noiseless
simulator; the measured bitstrings are scored classically. It demonstrates and benchmarks the
quantum search step. It does not offer a quantum advantage, because the marked set already is the
answer, and it is a one-shot search over all 2^n itemsets, not level-wise Apriori.

min_support=0.25 on this dataset marks 6 of 32 states, a sparse regime where Grover helps
(r_opt=1, ideal success probability about 0.95). The dense default of 0.05 marks 27 of 32 states,
where doing nothing already succeeds with probability 0.84 and Grover cannot help.
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
        min_support=0.25,
        grover_iterations=None,  # r_opt from the classically known M
        shots=8192,
        initial_state="uniform",
        diffusion="matched",
        marking="support",
        seed=42,
    )

    transactions = load_transactions(cfg.dataset_path)
    order = select_top_k_items(transactions, cfg.top_k_items)
    reduced = reduce_to_selected_items(transactions, order)
    truth = {frozenset(s) for s in brute_force_frequent_itemsets(reduced, cfg.min_support)}

    result = run_qfim_bench(
        cfg, ground_truth_frequent=truth, manifest_path="results/quickstart_run/manifest.json"
    )
    info = result.circuit_info
    marked_keys = {format(i, f"0{cfg.top_k_items}b") for i in info.marked_indices}
    p_marked = sum(c for k, c in result.execution.counts.items() if k in marked_keys) / cfg.shots

    print(f"items:               {order}")
    print(f"M of N marked:       {info.M} of {info.N}   (r used = {info.r}, r_opt from M)")
    print(f"theoretical P:       {info.theoretical_p:.4f}   (noiseless Grover, matched diffusion)")
    print(f"empirical P(marked): {p_marked:.4f}")
    m, b = result.metrics, result.baselines
    print(f"precision/recall/F1: {m.precision:.4f} / {m.recall:.4f} / {m.f1:.4f}")
    print(
        f"baseline 'everything frequent': {b['everything_frequent'].precision:.4f} / "
        f"{b['everything_frequent'].recall:.4f} / {b['everything_frequent'].f1:.4f}"
    )
    print(f"baseline 'random guess' F1:     {b['random_guess'].f1:.4f} +/- {b['random_guess'].sd_f1:.4f}")


if __name__ == "__main__":
    main()
