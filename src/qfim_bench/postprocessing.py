"""
postprocessing.py — Stage 5 of the qfim-bench pipeline: classical
containment counting, frequent/infrequent thresholding, and mining-quality
metrics.

Matches the companion paper's Methodology:

    sup_hat(X) = (sum of c_b over measured bitstrings b where X subset-of X_b) / S     (Eq. 5)

    tau = ceil(min_support * S * alpha)

    Precision = TP/(TP+FP), Recall = TP/(TP+FN),
    F1 = 2*Precision*Recall/(Precision+Recall)                                        (Eq. 6)

An itemset is declared frequent if its containment count meets tau.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .encoding import all_nonempty_subsets, decode_bitstring_to_itemset


def containment_support(
    counts: dict[str, int],
    itemset: set[str],
    item_order: list[str],
    shots: int,
) -> float:
    """
    Eq. (5): fraction of shots whose measured bitstring's itemset contains
    `itemset` as a subset. counts is a Qiskit-style {bitstring: count}
    dict; item_order must match the ordering used to build the circuit
    that produced these counts.
    """
    if shots <= 0:
        raise ValueError("shots must be positive")

    total = 0
    for bits, c in counts.items():
        measured_itemset = decode_bitstring_to_itemset(bits, item_order)
        if itemset.issubset(measured_itemset):
            total += c
    return total / shots


def support_threshold(min_support: float, shots: int, alpha: float) -> int:
    """tau = ceil(min_support * shots * alpha) — Methodology, just before Eq. (5)."""
    if not (0 < min_support <= 1):
        raise ValueError("min_support must be in (0, 1]")
    if not (0 < alpha <= 1):
        raise ValueError("alpha must be in (0, 1]")
    return math.ceil(min_support * shots * alpha)


@dataclass
class MinedItemset:
    itemset: set[str]
    containment_count: int
    estimated_support: float
    is_frequent: bool


def mine_frequent_itemsets(
    counts: dict[str, int],
    item_order: list[str],
    min_support: float,
    alpha: float,
) -> list[MinedItemset]:
    """
    Score every non-empty candidate itemset (all 2^m - 1 subsets of
    item_order) against the measured counts, and classify each as
    frequent/infrequent against tau = support_threshold(...). Returns one
    MinedItemset per candidate, in the same deterministic order as
    all_nonempty_subsets() produces, so results are reproducible run to
    run for identical inputs.
    """
    shots = sum(counts.values())
    tau = support_threshold(min_support, shots, alpha)

    results = []
    for itemset in all_nonempty_subsets(item_order):
        raw_count = 0
        for bits, c in counts.items():
            measured_itemset = decode_bitstring_to_itemset(bits, item_order)
            if itemset.issubset(measured_itemset):
                raw_count += c
        results.append(
            MinedItemset(
                itemset=itemset,
                containment_count=raw_count,
                estimated_support=raw_count / shots,
                is_frequent=raw_count >= tau,
            )
        )
    return results


@dataclass
class ClassificationMetrics:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


def precision_recall_f1(
    predicted_frequent: set[frozenset[str]],
    ground_truth_frequent: set[frozenset[str]],
) -> ClassificationMetrics:
    """
    Eq. (6). Itemsets must be passed as sets of frozensets (itemsets are
    themselves sets, which aren't hashable — frozenset is the hashable
    equivalent, used here purely so predicted/ground-truth can be compared
    with set operations).

    TP = predicted and ground-truth agree frequent; FP = predicted
    frequent but not in ground truth; FN = in ground truth but not
    predicted frequent.
    """
    tp = len(predicted_frequent & ground_truth_frequent)
    fp = len(predicted_frequent - ground_truth_frequent)
    fn = len(ground_truth_frequent - predicted_frequent)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return ClassificationMetrics(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1)
