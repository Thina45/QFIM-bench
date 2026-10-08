"""Does the measured output depend on the dataset?  (task a, STOP-GATE 2)

Runs the pipeline on two different transaction datasets with identical n, threshold, r, seed and
shots. With the v1 cardinality oracle (marks itemsets by SIZE) and the uniform start, the circuit
contains no data at all, so the counts must be identical. With the data-driven oracle the marked
set comes from the data, so the counts must differ.

It also records what the v1 precision/recall/F1 actually measure, by comparing them with the
trivial "everything is frequent" baseline.

    python analysis/data_independence.py --seed 42
"""

import argparse
import json
import random
import tempfile
from pathlib import Path

from qfim_bench.classical import brute_force_frequent_itemsets
from qfim_bench.config import QFIMConfig
from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.pipeline import run_qfim_bench
from qfim_bench.postprocessing import trivial_baselines
from qfim_bench.preprocessing import load_transactions, reduce_to_selected_items, select_top_k_items

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
ITEMS = [f"item_{i}" for i in range(8)]


def make_dataset(path: Path, seed: int, weights: list[float], n_tx: int = 300) -> None:
    rng = random.Random(seed)
    rows = []
    for _ in range(n_tx):
        k = rng.randint(1, 5)
        basket: set[str] = set()
        while len(basket) < k:
            basket.add(rng.choices(ITEMS, weights=weights)[0])
        rows.append(",".join(sorted(basket)))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def make_clustered_dataset(path: Path, seed: int, n_tx: int = 300) -> None:
    """Items co-occur in two themes, so pair/triple supports differ from an independent-items dataset."""
    rng = random.Random(seed)
    themes = [ITEMS[0:3], ITEMS[3:6]]
    rows = []
    for _ in range(n_tx):
        theme = rng.choice(themes)
        basket = {i for i in theme if rng.random() < 0.8}
        if rng.random() < 0.15:
            basket.add(rng.choice(ITEMS))
        if not basket:
            basket.add(rng.choice(theme))
        rows.append(",".join(sorted(basket)))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_one(path: Path, seed: int, **cfg_kwargs):
    cfg = QFIMConfig(dataset_path=str(path), top_k_items=5, shots=8192, seed=seed, **cfg_kwargs)
    tx = load_transactions(str(path))
    order = select_top_k_items(tx, 5)
    reduced = reduce_to_selected_items(tx, order)
    truth = {frozenset(s) for s in brute_force_frequent_itemsets(reduced, cfg.min_support)}
    res = run_qfim_bench(cfg, ground_truth_frequent=truth)
    predicted = [m for m in res.mined_itemsets if m.is_frequent]
    return {
        "item_order": order,
        "ground_truth_size": len(truth),
        "M": res.circuit_info.M,
        "marked_indices": list(res.circuit_info.marked_indices),
        "r": res.circuit_info.r,
        "predicted_frequent_size": len(predicted),
        "n_candidates": len(res.mined_itemsets),
        "precision": res.metrics.precision,
        "recall": res.metrics.recall,
        "f1": res.metrics.f1,
        "everything_frequent_baseline": {
            "precision": res.baselines["everything_frequent"].precision,
            "recall": res.baselines["everything_frequent"].recall,
            "f1": res.baselines["everything_frequent"].f1,
        },
        "counts": res.execution.counts,
    }


def tvd(c1: dict, c2: dict) -> float:
    n1, n2 = sum(c1.values()), sum(c2.values())
    keys = set(c1) | set(c2)
    return 0.5 * sum(abs(c1.get(k, 0) / n1 - c2.get(k, 0) / n2) for k in keys)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "A.csv", Path(tmp) / "B.csv"
        make_dataset(a, seed=1, weights=[0.45, 0.40, 0.35, 0.30, 0.28, 0.10, 0.10, 0.08])
        make_clustered_dataset(b, seed=2)

        result = {"seed": args.seed}
        for label, kwargs in {
            "cardinality_oracle_v1": dict(marking="cardinality", oracle_threshold=2, grover_iterations=2),
            "data_driven_oracle": dict(marking="support", min_support=0.25, grover_iterations=None),
        }.items():
            ra = run_one(a, args.seed, **kwargs)
            rb = run_one(b, args.seed, **kwargs)
            result[label] = {
                "counts_identical": ra["counts"] == rb["counts"],
                "tvd_between_datasets": tvd(ra["counts"], rb["counts"]),
                "dataset_A": {k: v for k, v in ra.items() if k != "counts"},
                "dataset_B": {k: v for k, v in rb.items() if k != "counts"},
            }

    (OUT / "data_independence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_experiment_manifest(str(OUT / "data_independence_manifest.json"),
                              {"seed": args.seed, "script": "analysis/data_independence.py"}, overwrite=True)
    for label in ("cardinality_oracle_v1", "data_driven_oracle"):
        r = result[label]
        print(f"{label}: counts identical across datasets = {r['counts_identical']}  TVD = {r['tvd_between_datasets']:.4f}")
        for ds in ("dataset_A", "dataset_B"):
            d = r[ds]
            print(f"  {ds}: marked={d['marked_indices'] if d['M'] < 12 else str(d['M']) + ' states'} M={d['M']} r={d['r']} predicted {d['predicted_frequent_size']}/{d['n_candidates']} "
                  f"truth={d['ground_truth_size']}  P/R/F1={d['precision']:.4f}/{d['recall']:.4f}/{d['f1']:.4f}  "
                  f"all-frequent baseline F1={d['everything_frequent_baseline']['f1']:.4f}")


if __name__ == "__main__":
    main()
