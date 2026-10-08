"""Oracle accounting (per M, n=5) and item-count sweep (n=3..10), with explicit timeouts.

Writes two figure-ready CSVs to results/sim/:

  oracle_accounting_n5.csv   M in {1,2,3,4,6,26} on 5 items, all-to-all AND on FakeMarrakesh
  item_count_sweep.csv       n = 3..max-n for two marking rules: sparse (M=3) and dense (the v1
                             cardinality rule, threshold 2)

Every transpile runs in a child process with a hard timeout; a timeout is recorded as
transpile_status="timeout" and never replaced by an estimate.

    python analysis/oracle_scaling.py --timeout 120 --max-n 10
"""

import argparse
from pathlib import Path

from qfim_bench.circuit import cardinality_marked_indices
from qfim_bench.manifest import write_experiment_manifest
from qfim_bench.scaling import oracle_costs, oracle_costs_to_dataframe

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "sim"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds per transpile")
    ap.add_argument("--max-n", type=int, default=10)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []
    for M in (1, 2, 3, 4, 6):
        rows += oracle_costs(5, list(range(M)), f"explicit_M{M}",
                             targets=("all_to_all", "FakeMarrakesh"), timeout_seconds=args.timeout)
    rows += oracle_costs(5, cardinality_marked_indices(5, 2), "cardinality_t2_M26",
                         targets=("all_to_all", "FakeMarrakesh"), timeout_seconds=args.timeout)
    df1 = oracle_costs_to_dataframe(rows)
    df1.to_csv(OUT / "oracle_accounting_n5.csv", index=False)
    print(df1[df1.component == "oracle"][["M", "target", "logical_gates", "transpiled_depth",
                                          "transpiled_two_qubit_gates", "transpile_status"]].to_string(index=False))

    rows = []
    for n in range(3, args.max_n + 1):
        rows += oracle_costs(n, [0, 1, 2], "sparse_M3", timeout_seconds=args.timeout)
        rows += oracle_costs(n, cardinality_marked_indices(n, 2), "dense_cardinality_t2",
                             timeout_seconds=args.timeout)
        df = oracle_costs_to_dataframe(rows)
        df.to_csv(OUT / "item_count_sweep.csv", index=False)  # written after every n, so a stall loses nothing
        last = df[(df.n_items == n) & (df.component == "iteration")]
        print(f"n={n}: " + "; ".join(
            f"{r.marking} M={r.M} depth={r.transpiled_depth} 2Q={r.transpiled_two_qubit_gates} [{r.transpile_status}]"
            for r in last.itertuples()), flush=True)

    write_experiment_manifest(str(OUT / "oracle_scaling_manifest.json"),
                              {"timeout_seconds": args.timeout, "max_n": args.max_n,
                               "script": "analysis/oracle_scaling.py"}, overwrite=True)


if __name__ == "__main__":
    main()
