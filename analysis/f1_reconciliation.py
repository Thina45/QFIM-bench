"""Reconcile the two precision/recall/F1 triples that appear in the paper material.

  0.4516 / 1.0000 / 0.6222   conference paper (hardware campaign): primary_quantum.csv, 14 of the 31
                             non-empty itemsets are frequent at min_support 0.05.
  0.8710 / 1.0000 / 0.9310   software quickstart at its default min_support 0.05: the bundled
                             sample data, 27 of 31 itemsets are frequent.

Both are exactly the "everything frequent" baseline for their dataset: predict all 31 itemsets,
so recall is 1 and precision is (true count)/31. The script recomputes both from the data, runs the
package pipeline on the sample data (cardinality marking as in v1, and data-driven marking) and puts
each result next to the baselines. Nothing here uses a quantum device.

    python analysis/f1_reconciliation.py
"""

import json
from pathlib import Path

from qfim_bench.classical import brute_force_frequent_itemsets
from qfim_bench.config import QFIMConfig
from qfim_bench.encoding import all_nonempty_subsets
from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.pipeline import run_qfim_bench
from qfim_bench.postprocessing import precision_recall_f1, trivial_baselines
from qfim_bench.preprocessing import load_transactions, reduce_to_selected_items, select_top_k_items

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"
SAMPLE = ROOT / "data" / "sample_transactions.csv"
CONFERENCE_TRUTH = ROOT.parent.parent / "Conference" / "resubmission" / "results" / "processed" / "classical_ground_truth.json"


def triple(m) -> dict:
    return {"precision": m.precision, "recall": m.recall, "f1": m.f1}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []

    # --- conference dataset: use the committed classical ground truth, not the dataset itself -----
    if CONFERENCE_TRUTH.exists():
        gt = json.loads(CONFERENCE_TRUTH.read_text(encoding="utf-8"))
        items = gt["items"]
        truth = {frozenset(d["itemset"]) for d in gt["frequent_itemsets"]}
        everything = {frozenset(s) for s in all_nonempty_subsets(items)}
        m = precision_recall_f1(everything, truth)
        rows.append({"dataset": "primary_quantum.csv (conference)", "min_support": gt["min_support"],
                     "true_frequent": len(truth), "all_itemsets": len(everything),
                     "everything_frequent_baseline": triple(m),
                     "paper_reports": {"precision": 0.4516, "recall": 1.0, "f1": 0.6222}})

    # --- bundled sample data ---------------------------------------------------------------------
    tx = load_transactions(str(SAMPLE))
    order = select_top_k_items(tx, 5)
    reduced = reduce_to_selected_items(tx, order)
    everything = {frozenset(s) for s in all_nonempty_subsets(order)}
    for support, marking, r in ((0.05, "cardinality", 1), (0.05, "support", None), (0.25, "support", None)):
        truth = {frozenset(s) for s in brute_force_frequent_itemsets(reduced, support)}
        cfg = QFIMConfig(dataset_path=str(SAMPLE), top_k_items=5, min_support=support, marking=marking,
                         oracle_threshold=2, grover_iterations=r, initial_state="uniform", seed=42)
        res = run_qfim_bench(cfg, ground_truth_frequent=truth)
        base = trivial_baselines(everything, truth)
        rows.append({
            "dataset": "sample_transactions.csv (software)", "min_support": support, "marking": marking,
            "true_frequent": len(truth), "all_itemsets": len(everything), "M_marked": res.circuit_info.M,
            "r": res.circuit_info.r,
            "pipeline": triple(res.metrics),
            "everything_frequent_baseline": triple(base["everything_frequent"]),
            "random_guess_f1": base["random_guess"].f1,
        })

    for row in rows:
        print(json.dumps(row, indent=1))
    (OUT / "f1_reconciliation.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_experiment_manifest(str(OUT / "f1_reconciliation_manifest.json"),
                              {"script": "analysis/f1_reconciliation.py", "seed": 42}, overwrite=True)


if __name__ == "__main__":
    main()
