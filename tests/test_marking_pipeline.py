"""Data-driven marking, the end-to-end ordering test with ASYMMETRIC marked sets, baselines, and the
pipeline's marking modes.

The end-to-end tests go encode -> oracle -> simulator counts -> decode and compare with ground truth.
An asymmetric marked set is essential: a reversed item/qubit mapping decodes {item_0, item_2} as
{item_4, item_2}, which the symmetric Hamming-weight oracle could never reveal.
"""

import math

import pytest
from qiskit_aer import AerSimulator

from conftest import SAMPLE_CSV
from qfim_bench.circuit import build_grover_circuit, optimal_iterations
from qfim_bench.classical import brute_force_frequent_itemsets
from qfim_bench.config import QFIMConfig
from qfim_bench.encoding import decode_bitstring_to_itemset, encode_itemset_to_bitstring, itemset_to_index
from qfim_bench.marking import data_driven_marked_states
from qfim_bench.pipeline import run_qfim_bench
from qfim_bench.postprocessing import detected_states, detection_threshold, trivial_baselines
from qfim_bench.preprocessing import reduce_to_selected_items, select_top_k_items

ORDER = [f"item_{i}" for i in range(5)]
SHOTS = 8192


def run_counts(marked_itemsets, r, seed=1):
    marked = [itemset_to_index(set(s), ORDER) for s in marked_itemsets]
    qc, info = build_grover_circuit(5, 2, r, initial_state="uniform", marked_states=marked)
    counts = AerSimulator(seed_simulator=seed).run(qc, shots=SHOTS).result().get_counts()
    return counts, info


def five_sigma(p):
    return max(5.0 * math.sqrt(p * (1.0 - p) / SHOTS), 1e-3)


# ---------------------------------------------------------------- end to end, asymmetric marking

def test_single_asymmetric_itemset_round_trip():
    """Mark {item_0, item_2}; after r_opt iterations the dominant outcome decodes back to it."""
    target = {"item_0", "item_2"}
    r = optimal_iterations(1, 32)
    counts, info = run_counts([target], r)
    top_key = max(counts, key=counts.get)
    assert top_key == encode_itemset_to_bitstring(target, ORDER) == "00101"
    assert decode_bitstring_to_itemset(top_key, ORDER) == target
    assert abs(counts[top_key] / SHOTS - info.theoretical_p) < five_sigma(info.theoretical_p)


def test_two_asymmetric_itemsets_round_trip():
    """Mark {item_0, item_2} and {item_1}; detected states decode exactly to the marked itemsets."""
    truth = [{"item_0", "item_2"}, {"item_1"}]
    counts, _ = run_counts(truth, optimal_iterations(2, 32))
    decoded = {frozenset(decode_bitstring_to_itemset(k, ORDER)) for k in detected_states(counts)}
    assert decoded == {frozenset(t) for t in truth}


@pytest.mark.parametrize("target", [{f"item_{p}"} for p in range(5)])
def test_every_single_item_decodes_to_itself(target):
    counts, _ = run_counts([target], optimal_iterations(1, 32))
    assert decode_bitstring_to_itemset(max(counts, key=counts.get), ORDER) == target


# ---------------------------------------------------------------- detection threshold

def test_detection_threshold_is_a_function_of_shots_and_states_only():
    assert detection_threshold(8192, 32) == detection_threshold(8192, 32)
    assert detection_threshold(8192, 32) > 8192 / 32  # above the uniform mean of 256


def test_uniform_counts_flag_nothing():
    """r=0 is a uniform distribution, so the Bonferroni-corrected threshold flags nothing."""
    qc, _ = build_grover_circuit(5, 2, 0, initial_state="uniform", marked_states=[3])
    counts = AerSimulator(seed_simulator=3).run(qc, shots=SHOTS).result().get_counts()
    assert detected_states(counts) == set()


# ---------------------------------------------------------------- data-driven marking

def test_data_driven_marking_hand_computed():
    order = ["a", "b", "c"]
    tx = [{"a", "b"}, {"a", "b", "c"}, {"a"}, {"b", "c"}]
    # supports: a 3/4, b 3/4, c 2/4, ab 2/4, ac 1/4, bc 2/4, abc 1/4
    got = data_driven_marked_states(tx, order, 0.5)
    expected = sorted(itemset_to_index(s, order) for s in [{"a"}, {"b"}, {"c"}, {"a", "b"}, {"b", "c"}])
    assert got == expected


def test_data_driven_marking_rejects_empty_marked_set():
    with pytest.raises(ValueError):
        data_driven_marked_states([{"a"}, {"b"}], ["a", "b"], 0.9)


# ---------------------------------------------------------------- baselines

def test_everything_frequent_baseline_matches_m26_numbers():
    cands = [frozenset({f"x{i}"}) for i in range(32)]
    truth = set(cands[:26])
    b = trivial_baselines(cands, truth)["everything_frequent"]
    assert b.precision == pytest.approx(26 / 32)
    assert b.recall == 1.0
    assert b.f1 == pytest.approx(0.8966, abs=1e-4)


def test_nothing_and_random_baselines():
    cands = [frozenset({f"x{i}"}) for i in range(31)]
    truth = set(cands[:14])
    out = trivial_baselines(cands, truth, draws=1000, seed=5)
    assert out["nothing_frequent"].f1 == 0.0
    # random guess with p=1/2: recall mean 0.5, precision mean |T|/|C| (14/31)
    assert out["random_guess"].recall == pytest.approx(0.5, abs=0.03)
    assert out["random_guess"].precision == pytest.approx(14 / 31, abs=0.03)
    assert out["random_guess"].sd_f1 > 0


# ---------------------------------------------------------------- pipeline modes

@pytest.fixture(scope="module")
def sample_truth(transactions):
    order = select_top_k_items(transactions, 5)
    reduced = reduce_to_selected_items(transactions, order)
    return order, reduced


def test_pipeline_support_marking_recovers_ground_truth_when_sparse(sample_truth):
    """min_support 0.25 marks M=6 of 32 on the sample data; at r_opt the quantum pipeline's mined set
    equals the classical ground truth (precision = recall = 1), unlike the all-frequent baseline."""
    order, reduced = sample_truth
    cfg = QFIMConfig(dataset_path=str(SAMPLE_CSV), min_support=0.25, grover_iterations=None, seed=42)
    truth = {frozenset(s) for s in brute_force_frequent_itemsets(reduced, cfg.min_support)}
    result = run_qfim_bench(cfg, ground_truth_frequent=truth)
    assert result.circuit_info.M == 6
    assert result.circuit_info.r == optimal_iterations(6, 32) == 1
    assert result.metrics.precision == 1.0 and result.metrics.recall == 1.0
    assert result.baselines["everything_frequent"].f1 < 1.0


def test_pipeline_cardinality_mode_still_reproduces_v1(sample_truth):
    cfg = QFIMConfig(dataset_path=str(SAMPLE_CSV), marking="cardinality", oracle_threshold=2, grover_iterations=2)
    result = run_qfim_bench(cfg)
    assert result.circuit_info.M == 26


def test_pipeline_explicit_marking():
    cfg = QFIMConfig(dataset_path=str(SAMPLE_CSV), marking="explicit", marked_states=(5,), grover_iterations=None)
    result = run_qfim_bench(cfg)
    assert result.circuit_info.M == 1 and result.circuit_info.r == 4


def test_config_validation():
    with pytest.raises(ValueError):
        QFIMConfig(dataset_path="x", marking="explicit")
    with pytest.raises(ValueError):
        QFIMConfig(dataset_path="x", diffusion="bogus")
    with pytest.raises(ValueError):
        QFIMConfig(dataset_path="x", marking="bogus")
