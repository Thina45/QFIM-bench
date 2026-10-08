"""Preprocessing, classical baselines, backends and end-to-end pipeline on the sample data."""

import pytest

from qfim_bench.backends import HardwareBackend, SimulatorBackend, get_backend
from qfim_bench.classical import (
    brute_force_frequent_itemsets,
    run_apriori,
    run_classical_baseline,
    run_eclat,
    run_fpgrowth,
)
from qfim_bench.config import QFIMConfig
from qfim_bench.pipeline import run_qfim_bench
from qfim_bench.preprocessing import (
    load_transactions,
    reduce_to_selected_items,
    select_top_k_items,
)
from conftest import SAMPLE_CSV


@pytest.fixture(scope="module")
def transactions():
    return load_transactions(str(SAMPLE_CSV))


def test_sample_loads_ragged_rows(transactions):
    assert len(transactions) == 300
    assert all(len(t) >= 1 for t in transactions)


def test_top_k_selection_and_reduction(transactions):
    order = select_top_k_items(transactions, 5)
    assert len(order) == 5
    reduced = reduce_to_selected_items(transactions, order)
    assert all(t <= set(order) for t in reduced)
    assert all(len(t) >= 1 for t in reduced)


@pytest.mark.parametrize("min_support", [0.05, 0.10, 0.20])
def test_classical_algorithms_agree_with_brute_force(transactions, min_support):
    order = select_top_k_items(transactions, 5)
    reduced = reduce_to_selected_items(transactions, order)
    truth = set(brute_force_frequent_itemsets(reduced, min_support))
    assert set(run_apriori(reduced, min_support).frequent_itemsets) == truth
    assert set(run_eclat(reduced, min_support).frequent_itemsets) == truth
    assert set(run_fpgrowth(reduced, min_support).frequent_itemsets) == truth


def test_run_classical_baseline_returns_all_three(transactions):
    out = run_classical_baseline(transactions, 0.05)
    assert set(out) == {"apriori", "eclat", "fpgrowth"}
    # mlxtend is installed in the test environment, so FP-Growth must not be on the fallback path
    assert out["fpgrowth"].algorithm_note == ""


def test_simulator_bell_state_counts():
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    counts = SimulatorBackend(seed=42).run(qc, shots=4000).counts
    assert set(counts) <= {"00", "11"}
    assert abs(counts.get("00", 0) / 4000 - 0.5) < 0.05


def test_hardware_backend_refuses_without_credentials(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    from qiskit import QuantumCircuit

    with pytest.raises(RuntimeError):
        HardwareBackend().run(QuantumCircuit(1), shots=8192)


def test_get_backend_unknown_name():
    with pytest.raises(ValueError):
        get_backend("nope")


def test_end_to_end_pipeline_on_sample(transactions):
    cfg = QFIMConfig(
        dataset_path=str(SAMPLE_CSV),
        top_k_items=5,
        grover_iterations=1,
        shots=8192,
        initial_state="uniform",
        seed=42,
    )
    order = select_top_k_items(transactions, 5)
    reduced = reduce_to_selected_items(transactions, order)
    truth = set(brute_force_frequent_itemsets(reduced, cfg.min_support))

    result = run_qfim_bench(cfg, ground_truth_frequent=truth)
    # Default marking is data-driven, so the marked set is exactly the ground truth.
    assert result.circuit_info.M == len(truth) == 27
    # The v1 cardinality rule (threshold 2) is data-independent and marks 26 of 32.
    v1 = QFIMConfig(dataset_path=str(SAMPLE_CSV), top_k_items=5, grover_iterations=1,
                    initial_state="uniform", marking="cardinality", seed=42)
    assert run_qfim_bench(v1, ground_truth_frequent=truth).circuit_info.M == 26
    assert result.metrics is not None
    assert 0.0 <= result.metrics.precision <= 1.0
    assert result.metrics.recall >= 0.9  # the post-processing threshold is permissive by design
    assert sum(result.execution.counts.values()) == 8192


@pytest.mark.parametrize("min_support", [0.05, 0.10, 0.20])
def test_fpgrowth_uses_real_mlxtend_not_fallback(transactions, min_support):
    result = run_fpgrowth(transactions, min_support)
    # If mlxtend is installed and importing correctly, algorithm_note must
    # be empty — a non-empty note means it silently fell back to brute
    # force, which would make this test pass for the wrong reason.
    assert result.algorithm_note == "", (
        f"run_fpgrowth fell back to brute force: {result.algorithm_note!r}. "
        "mlxtend is installed in this environment — the real branch should run."
    )


@pytest.mark.parametrize("min_support", [0.05, 0.10, 0.20])
def test_fpgrowth_mlxtend_agrees_with_brute_force(transactions, min_support):
    truth = set(brute_force_frequent_itemsets(transactions, min_support))
    fp = run_fpgrowth(transactions, min_support)
    assert fp.algorithm_note == ""  # confirm real path again, don't pass on a fallback match
    assert set(fp.frequent_itemsets) == truth
