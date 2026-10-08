"""Phase 2F: a real public dataset (UCI Online Retail subset, CC BY 4.0, see data/README.md).

Classical baselines (brute force, Apriori, ECLAT, FP-Growth) on the full 50-item basket file and on
the top-5-item reduction, then the quantum pipeline (noiseless simulator, data-driven marking, r_opt)
on the same 5 items, each result next to the trivial baselines. min_support is varied over a grid
fixed in advance: 0.02, 0.03, 0.05, 0.08, 0.12.

Nothing here touches a quantum device. This is a software demonstration on real data, and the
marked set is the classical answer, so it carries the same "no advantage" caveat as everywhere else.

    python analysis/public_dataset.py
"""

import json
from pathlib import Path

from qfim_bench.classical import brute_force_frequent_itemsets, run_classical_baseline
from qfim_bench.config import QFIMConfig
from qfim_bench.encoding import all_nonempty_subsets, decode_bitstring_to_itemset
from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.pipeline import run_qfim_bench
from qfim_bench.postprocessing import detected_states, precision_recall_f1, trivial_baselines
from qfim_bench.preprocessing import load_transactions, reduce_to_selected_items, select_top_k_items

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "online_retail_baskets.csv"
OUT = ROOT / "results" / "sim"
GRID = (0.02, 0.03, 0.05, 0.08, 0.12)


def main() -> None:
    tx = load_transactions(str(DATA))
    order = select_top_k_items(tx, 5)
    reduced = reduce_to_selected_items(tx, order)
    everything = {frozenset(s) for s in all_nonempty_subsets(order)}
    out = {"dataset": "online_retail_baskets.csv", "baskets": len(tx), "items5": order, "rows": []}
    for support in GRID:
        truth = {frozenset(s) for s in brute_force_frequent_itemsets(reduced, support)}
        classical = run_classical_baseline(reduced, support)
        row = {"min_support": support, "true_frequent": len(truth),
               "classical": {k: {"itemsets": len(v.frequent_itemsets), "matches_brute_force": set(v.frequent_itemsets) == truth,
                                 "runtime_s": v.runtime_seconds, "peak_kb": v.peak_memory_bytes / 1024}
                             for k, v in classical.items()}}
        if truth:
            cfg = QFIMConfig(dataset_path=str(DATA), top_k_items=5, min_support=support, marking="support",
                             grover_iterations=None, initial_state="uniform", seed=42)
            res = run_qfim_bench(cfg, ground_truth_frequent=truth)
            base = trivial_baselines(everything, truth)
            detected = {frozenset(decode_bitstring_to_itemset(b, order)) for b in detected_states(res.execution.counts)}
            det = precision_recall_f1(detected, truth)
            row["quantum_noiseless"] = {"M": res.circuit_info.M, "r": res.circuit_info.r,
                                        "theoretical_p": res.circuit_info.theoretical_p,
                                        "containment_rule": {"precision": res.metrics.precision, "recall": res.metrics.recall,
                                                             "f1": res.metrics.f1},
                                        "detected_states": {"precision": det.precision, "recall": det.recall, "f1": det.f1}}
            row["everything_frequent_f1"] = base["everything_frequent"].f1
        out["rows"].append(row)
        q = row.get("quantum_noiseless")
        print(f"support {support}: true={len(truth)}/31  all classical match={all(c['matches_brute_force'] for c in row['classical'].values())}  "
              + (f"quantum M={q['M']} r={q['r']} F1 containment-rule={q['containment_rule']['f1']:.3f} detected-states={q['detected_states']['f1']:.3f} (everything-frequent {row['everything_frequent_f1']:.3f})" if q else "no frequent itemsets"))
    (OUT / "public_dataset.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    write_experiment_manifest(str(OUT / "public_dataset_manifest.json"),
                              {"script": "analysis/public_dataset.py", "grid": list(GRID)}, overwrite=True)


if __name__ == "__main__":
    main()
