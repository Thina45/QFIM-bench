"""
pipeline.py — single public entry point for qfim-bench: run_qfim_bench(config).

Wires together all five pipeline stages (companion paper, "Proposed
Hardware-Oriented Experimental Framework"):

    1. preprocessing.py  — classical item selection, frequency ranking
    2. encoding.py        — item <-> qubit mapping (fixed item_order)
    3. circuit.py          — Grover-based QFIM circuit construction
    4. backends.py         — execution (simulator by default)
    5. postprocessing.py  — containment counting, thresholding, metrics

A user's entire interaction is intended to be:

    from qfim_bench.config import QFIMConfig
    from qfim_bench.pipeline import run_qfim_bench

    result = run_qfim_bench(QFIMConfig(dataset_path="data.csv", top_k_items=5))

Everything else (noise_analysis, reproducibility, scaling, classical) is
opt-in via separate function calls on the pieces this module exposes
(result.circuit, result.circuit_info, result.backend), not bundled into
every run by default — a basic simulator run should stay fast and simple.
"""

from __future__ import annotations

from dataclasses import dataclass

from .backends import Backend, ExecutionResult, get_backend
from .circuit import CircuitInfo, build_grover_circuit
from .config import QFIMConfig
from .encoding import all_nonempty_subsets
from .postprocessing import (
    ClassificationMetrics,
    MinedItemset,
    mine_frequent_itemsets,
    precision_recall_f1,
)
from .manifest import write_experiment_manifest
from .preprocessing import load_transactions, reduce_to_selected_items, select_top_k_items


@dataclass
class QFIMBenchResult:
    config: QFIMConfig
    item_order: list[str]
    circuit_info: CircuitInfo
    execution: ExecutionResult
    mined_itemsets: list[MinedItemset]
    backend: Backend  # kept so callers can reuse it for noise_analysis/reproducibility
    ground_truth_frequent: set[frozenset[str]] | None = None
    metrics: ClassificationMetrics | None = None


def run_qfim_bench(
    config: QFIMConfig,
    ground_truth_frequent: set[frozenset[str]] | None = None,
    manifest_path: str | None = None,
) -> QFIMBenchResult:
    """
    Run the full 5-stage QFIM pipeline for the given config, and return a
    QFIMBenchResult bundling everything downstream analysis needs:
    mined itemsets, the built circuit's metadata, the raw execution
    result, and (if ground_truth_frequent is supplied) precision/recall/F1
    against it.

    ground_truth_frequent is optional because a user exploring a new
    dataset may not have a known-correct answer to compare against yet —
    in that case, use classical.brute_force_frequent_itemsets(...) on the
    same (reduced) transactions first to obtain one, matching the
    companion paper's own methodology (Section 3, "Classical Ground
    Truth").
    """
    # Stage 1: preprocessing
    transactions = load_transactions(config.dataset_path)
    item_order = select_top_k_items(transactions, config.top_k_items)
    reduced_transactions = reduce_to_selected_items(transactions, item_order)

    # Stage 2 (encoding) has no separate step here — item_order IS the
    # encoding; circuit.py and postprocessing.py both take it directly.

    # Stage 3: circuit construction. initial_state and seed are threaded
    # through explicitly: "uniform" (default) reproduces Eq. (4) exactly in
    # simulation; "ansatz" reproduces the companion paper's hardware
    # circuit (flat even without noise — see README).
    circuit, circuit_info = build_grover_circuit(
        n_items=config.top_k_items,
        threshold=config.oracle_threshold,
        r=config.grover_iterations,
        reps=config.ansatz_reps,
        initial_state=config.initial_state,
        seed=config.seed,
    )

    # Stage 4: execution. Only aer_simulator and noisy_simulator accept a
    # seed kwarg (HardwareBackend does not — there's no "seed" concept for
    # real hardware), so seed is passed conditionally rather than always,
    # to avoid a TypeError when config.backend == "ibm_hardware".
    backend_kwargs = {"seed": config.seed} if config.backend in ("aer_simulator", "noisy_simulator") else {}
    backend = get_backend(config.backend, **backend_kwargs)
    execution = backend.run(circuit, shots=config.shots)

    # Stage 5: post-processing
    mined = mine_frequent_itemsets(
        counts=execution.counts,
        item_order=item_order,
        min_support=config.min_support,
        alpha=config.alpha,
    )

    result = QFIMBenchResult(
        config=config,
        item_order=item_order,
        circuit_info=circuit_info,
        execution=execution,
        mined_itemsets=mined,
        backend=backend,
        ground_truth_frequent=ground_truth_frequent,
    )

    if ground_truth_frequent is not None:
        predicted = {frozenset(m.itemset) for m in mined if m.is_frequent}
        result.metrics = precision_recall_f1(predicted, ground_truth_frequent)

    if manifest_path is not None:
        write_experiment_manifest(
            manifest_path,
            config,
            extra={
                "item_order": item_order,
                "circuit_info": {
                    "n_items": result.circuit_info.n_items,
                    "threshold": result.circuit_info.threshold,
                    "r": result.circuit_info.r,
                    "M": result.circuit_info.M,
                    "N": result.circuit_info.N,
                    "theoretical_p": result.circuit_info.theoretical_p,
                },
                "shots": result.execution.shots,
                "backend_name": result.execution.backend_name,
            },
        )

    return result
