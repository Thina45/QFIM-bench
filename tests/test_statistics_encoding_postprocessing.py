"""Pure-logic tests: statistics, encoding round-trips, and the paper's post-processing values."""

import math

import pytest

from qfim_bench.encoding import (
    all_nonempty_subsets,
    decode_bitstring_to_itemset,
    encode_itemset_to_bitstring,
)
from qfim_bench.postprocessing import precision_recall_f1, support_threshold
from qfim_bench.statistics import summarize_runs, total_variation_distance

ORDER = ["mineral water", "eggs", "spaghetti", "french fries", "chocolate"]


# ---- statistics -----------------------------------------------------------

def test_summarize_runs_hand_computed():
    s = summarize_runs([1, 2, 3, 4, 5])
    assert s.mean == pytest.approx(3.0)
    assert s.sd == pytest.approx(math.sqrt(2.5))
    assert s.cv_percent == pytest.approx(100 * math.sqrt(2.5) / 3.0)


def test_tvd_hand_verified():
    p = {"a": 0.5, "b": 0.5}
    q = {"a": 1.0, "b": 0.0}
    assert total_variation_distance(p, q) == pytest.approx(0.5)
    assert total_variation_distance(p, p) == pytest.approx(0.0)


# ---- encoding -------------------------------------------------------------

def test_encode_decode_round_trip_all_subsets():
    for subset in all_nonempty_subsets(ORDER):
        bits = encode_itemset_to_bitstring(subset, ORDER)
        assert len(bits) == len(ORDER)
        assert decode_bitstring_to_itemset(bits, ORDER) == set(subset)


def test_all_nonempty_subsets_count():
    assert len(all_nonempty_subsets(ORDER)) == 31


# ---- post-processing (paper values) --------------------------------------

def test_support_threshold_is_41_counts():
    # tau = ceil(0.05 * 8192 * 0.1) = ceil(40.96) = 41
    assert support_threshold(0.05, 8192, 0.1) == 41


def test_paper_precision_recall_f1():
    # TP=14, FP=17, FN=0 -> precision 0.4516, recall 1.0000, F1 0.6222
    truth = {frozenset({f"x{i}"}) for i in range(14)}
    predicted = truth | {frozenset({f"y{i}"}) for i in range(17)}
    m = precision_recall_f1(predicted, truth)
    assert m.precision == pytest.approx(0.4516, abs=1e-4)
    assert m.recall == pytest.approx(1.0)
    assert m.f1 == pytest.approx(0.6222, abs=1e-4)
