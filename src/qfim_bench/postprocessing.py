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


# --------------------------------------------------------------------------
# Trivial baselines: what precision/recall/F1 a method with no information achieves
# --------------------------------------------------------------------------

@dataclass
class BaselineMetrics:
    """Precision/recall/F1 of an uninformed predictor. sd_* are 0 for deterministic baselines."""
    name: str
    precision: float
    recall: float
    f1: float
    sd_precision: float = 0.0
    sd_recall: float = 0.0
    sd_f1: float = 0.0


def trivial_baselines(
    candidates: list[frozenset[str]],
    ground_truth_frequent: set[frozenset[str]],
    draws: int = 1000,
    seed: int = 0,
) -> dict[str, BaselineMetrics]:
    """
    Baselines to report next to every precision/recall/F1 figure, so a score is never read without
    knowing what doing nothing clever achieves.

    - "everything_frequent": predict every candidate frequent. precision = |T|/|C|, recall = 1,
      F1 = 2P/(P+1). For M=26 of 32 this is 0.8125 / 1.0 / 0.897.
    - "nothing_frequent": predict none. precision, recall and F1 are all 0 (precision 0/0 is
      defined as 0 here, as in precision_recall_f1).
    - "random_guess": include each candidate independently with probability 1/2; mean and standard
      deviation over `draws` seeded draws.
    """
    import numpy as np

    truth = set(ground_truth_frequent) & set(candidates)
    n_c = len(candidates)
    if n_c == 0:
        raise ValueError("candidates is empty")

    p_all = len(truth) / n_c
    f_all = 2 * p_all / (p_all + 1) if (p_all + 1) > 0 else 0.0
    out = {
        "everything_frequent": BaselineMetrics("everything_frequent", p_all, 1.0 if truth else 0.0, f_all),
        "nothing_frequent": BaselineMetrics("nothing_frequent", 0.0, 0.0, 0.0),
    }

    rng = np.random.default_rng(seed)
    precs, recs, f1s = [], [], []
    for _ in range(draws):
        mask = rng.random(n_c) < 0.5
        predicted = {c for c, m in zip(candidates, mask) if m}
        m_ = precision_recall_f1(predicted, truth)
        precs.append(m_.precision)
        recs.append(m_.recall)
        f1s.append(m_.f1)
    out["random_guess"] = BaselineMetrics(
        "random_guess",
        float(np.mean(precs)), float(np.mean(recs)), float(np.mean(f1s)),
        float(np.std(precs, ddof=1)), float(np.std(recs, ddof=1)), float(np.std(f1s, ddof=1)),
    )
    return out


# --------------------------------------------------------------------------
# Detecting amplified basis states from raw counts
# --------------------------------------------------------------------------

def detection_threshold(shots: int, n_states: int, alpha: float = 0.05) -> int:
    """
    Smallest count c such that a state with count > c is unlikely under the uniform null.

    Under no amplification each of the n_states outcomes has count ~ Binomial(shots, 1/n_states).
    This returns the Bonferroni-corrected upper quantile binom.isf(alpha / n_states), so across all
    n_states outcomes the chance that a purely uniform run flags any state is at most alpha. It is
    a function of (shots, n_states, alpha) only, so it can be fixed before any data is seen.
    """
    from scipy.stats import binom

    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    return int(binom.isf(alpha / n_states, shots, 1.0 / n_states))


def detected_states(counts: dict[str, int], alpha: float = 0.05) -> set[str]:
    """Count keys whose count exceeds detection_threshold: the states the run actually amplified."""
    if not counts:
        return set()
    shots = sum(counts.values())
    n_states = 2 ** len(next(iter(counts)))
    threshold = detection_threshold(shots, n_states, alpha)
    return {key for key, c in counts.items() if c > threshold}
