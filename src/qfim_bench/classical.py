"""
classical.py — Stage 7: classical frequent itemset mining baselines, for
direct side-by-side comparison against the quantum pipeline (companion
paper, Section 6: "division of labor" between classical and quantum FIM).

Apriori and ECLAT are implemented here in pure Python (no third-party
dependency), since both are simple enough to implement correctly and
testably, and a dependency-free baseline module is one less thing that can
break a fresh install. FP-Growth uses mlxtend if installed (pip install
qfim-bench[classical-fpgrowth]) since a correct, efficient FP-tree
implementation is substantial; if mlxtend is not installed,
run_fpgrowth falls back to the same brute-force enumeration used for
ground truth, raising no error but clearly labeling the result as a
fallback (not actual FP-Growth) via ClassicalResult.algorithm_note.

All three (plus the brute-force ground truth) are guaranteed to return the
same set of frequent itemsets for the same (transactions, min_support) —
this agreement is itself a correctness check worth asserting in tests,
exactly as the companion paper reports all three algorithms as finding the
same answer on its full dataset.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from itertools import combinations


@dataclass
class ClassicalResult:
    algorithm: str
    frequent_itemsets: list[frozenset[str]]
    min_support: float
    runtime_seconds: float
    peak_memory_bytes: int
    algorithm_note: str = ""


def _support_counts(transactions: list[set[str]]) -> dict[str, int]:
    """Count how many transactions contain each individual item."""
    counts: dict[str, int] = {}
    for t in transactions:
        for item in t:
            counts[item] = counts.get(item, 0) + 1
    return counts


def brute_force_frequent_itemsets(
    transactions: list[set[str]], min_support: float
) -> list[frozenset[str]]:
    """
    Exact ground truth: enumerate every non-empty subset of the universe
    of items appearing in `transactions` and keep those meeting
    min_support. Exponential in the number of distinct items — intended
    for small item universes (matching the companion paper's own
    ground-truth derivation: "brute-force enumeration of all 31 non-empty
    subsets"), not for the full-scale classical baseline (use
    run_apriori/run_eclat/run_fpgrowth for that).
    """
    n = len(transactions)
    if n == 0:
        return []

    universe = sorted({item for t in transactions for item in t})
    frequent = []
    for size in range(1, len(universe) + 1):
        for combo in combinations(universe, size):
            itemset = frozenset(combo)
            count = sum(1 for t in transactions if itemset.issubset(t))
            if count / n >= min_support:
                frequent.append(itemset)
    return frequent


def _run_timed(fn, *args, **kwargs):
    """Run fn, measuring wall-clock time and peak memory via tracemalloc."""
    tracemalloc.start()
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed, peak


# --------------------------------------------------------------------------
# Apriori (level-wise candidate generation with downward-closure pruning)
# --------------------------------------------------------------------------

def _apriori_core(transactions: list[set[str]], min_support: float) -> list[frozenset[str]]:
    n = len(transactions)
    if n == 0:
        return []

    item_counts = _support_counts(transactions)
    frequent_1 = {
        frozenset([item]) for item, c in item_counts.items() if c / n >= min_support
    }

    all_frequent: list[frozenset[str]] = list(frequent_1)
    current_level = frequent_1
    k = 2

    while current_level:
        # Candidate generation: join frequent (k-1)-itemsets that share a
        # (k-2)-prefix, matching the standard Apriori join step.
        current_list = sorted(current_level, key=lambda fs: sorted(fs))
        candidates = set()
        for i in range(len(current_list)):
            for j in range(i + 1, len(current_list)):
                a, b = sorted(current_list[i]), sorted(current_list[j])
                if a[:-1] == b[:-1]:
                    candidates.add(frozenset(current_list[i] | current_list[j]))

        # Downward-closure pruning: a candidate can only be frequent if
        # every (k-1)-subset of it is frequent.
        pruned = {
            c for c in candidates
            if all(frozenset(sub) in current_level for sub in combinations(c, k - 1))
        }

        next_level = set()
        for candidate in pruned:
            count = sum(1 for t in transactions if candidate.issubset(t))
            if count / n >= min_support:
                next_level.add(candidate)

        all_frequent.extend(next_level)
        current_level = next_level
        k += 1

    return all_frequent


def run_apriori(transactions: list[set[str]], min_support: float) -> ClassicalResult:
    itemsets, elapsed, peak = _run_timed(_apriori_core, transactions, min_support)
    return ClassicalResult(
        algorithm="apriori",
        frequent_itemsets=itemsets,
        min_support=min_support,
        runtime_seconds=elapsed,
        peak_memory_bytes=peak,
    )


# --------------------------------------------------------------------------
# ECLAT (vertical tid-set intersection)
# --------------------------------------------------------------------------

def _eclat_core(transactions: list[set[str]], min_support: float) -> list[frozenset[str]]:
    n = len(transactions)
    if n == 0:
        return []

    min_count = min_support * n

    # Vertical representation: item -> set of transaction indices containing it.
    tidsets: dict[str, set[int]] = {}
    for idx, t in enumerate(transactions):
        for item in t:
            tidsets.setdefault(item, set()).add(idx)

    frequent_items = {
        frozenset([item]): tids for item, tids in tidsets.items() if len(tids) >= min_count
    }

    all_frequent: list[frozenset[str]] = list(frequent_items.keys())

    def extend(prefix_itemsets: dict[frozenset[str], set[int]]) -> None:
        items = sorted(prefix_itemsets.keys(), key=lambda fs: sorted(fs))
        for i in range(len(items)):
            new_level: dict[frozenset[str], set[int]] = {}
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                # Only combine itemsets sharing all but their last element,
                # matching ECLAT's standard equivalence-class extension.
                a_sorted, b_sorted = sorted(a), sorted(b)
                if a_sorted[:-1] != b_sorted[:-1]:
                    continue
                combined = frozenset(a | b)
                combined_tids = prefix_itemsets[a] & prefix_itemsets[b]
                if len(combined_tids) >= min_count:
                    new_level[combined] = combined_tids
            if new_level:
                all_frequent.extend(new_level.keys())
                extend(new_level)

    extend(frequent_items)
    return all_frequent


def run_eclat(transactions: list[set[str]], min_support: float) -> ClassicalResult:
    itemsets, elapsed, peak = _run_timed(_eclat_core, transactions, min_support)
    return ClassicalResult(
        algorithm="eclat",
        frequent_itemsets=itemsets,
        min_support=min_support,
        runtime_seconds=elapsed,
        peak_memory_bytes=peak,
    )


# --------------------------------------------------------------------------
# FP-Growth (via mlxtend if available, else a labeled brute-force fallback)
# --------------------------------------------------------------------------

def run_fpgrowth(transactions: list[set[str]], min_support: float) -> ClassicalResult:
    try:
        import pandas as pd
        from mlxtend.frequent_patterns import fpgrowth
        from mlxtend.preprocessing import TransactionEncoder

        def _mlxtend_fpgrowth():
            te = TransactionEncoder()
            te_array = te.fit(transactions).transform([list(t) for t in transactions])
            df = pd.DataFrame(te_array, columns=te.columns_)
            result_df = fpgrowth(df, min_support=min_support, use_colnames=True)
            return [frozenset(itemset) for itemset in result_df["itemsets"]]

        itemsets, elapsed, peak = _run_timed(_mlxtend_fpgrowth)
        return ClassicalResult(
            algorithm="fpgrowth",
            frequent_itemsets=itemsets,
            min_support=min_support,
            runtime_seconds=elapsed,
            peak_memory_bytes=peak,
        )
    except ImportError:
        itemsets, elapsed, peak = _run_timed(
            brute_force_frequent_itemsets, transactions, min_support
        )
        return ClassicalResult(
            algorithm="fpgrowth",
            frequent_itemsets=itemsets,
            min_support=min_support,
            runtime_seconds=elapsed,
            peak_memory_bytes=peak,
            algorithm_note=(
                "mlxtend not installed — fell back to brute-force enumeration. "
                "Install mlxtend for actual FP-Growth: pip install qfim-bench[classical-fpgrowth]"
            ),
        )


# --------------------------------------------------------------------------
# Convenience: run all three side by side
# --------------------------------------------------------------------------

def run_classical_baseline(
    transactions: list[set[str]], min_support: float
) -> dict[str, ClassicalResult]:
    """
    Run Apriori, ECLAT, and FP-Growth (or its fallback) on the same
    transactions/min_support, returning all three results keyed by
    algorithm name — for the side-by-side runtime/memory/itemset-count
    comparison in the companion paper's Table 2 style.
    """
    return {
        "apriori": run_apriori(transactions, min_support),
        "eclat": run_eclat(transactions, min_support),
        "fpgrowth": run_fpgrowth(transactions, min_support),
    }


@dataclass
class AssociationRule:
    antecedent: frozenset[str]
    consequent: frozenset[str]
    support: float          # support(antecedent U consequent)
    confidence: float       # support(antecedent U consequent) / support(antecedent)
    lift: float             # confidence / support(consequent)


def _support(itemset: frozenset[str], transactions: list[set[str]]) -> float:
    n = len(transactions)
    if n == 0:
        return 0.0
    return sum(1 for t in transactions if itemset.issubset(t)) / n


def generate_association_rules(
    transactions: list[set[str]],
    frequent_itemsets: list[frozenset[str]],
    min_confidence: float = 0.5,
) -> list[AssociationRule]:
    """
    Derive all association rules A -> B (A, B disjoint, A U B a known
    frequent itemset, B = (A U B) - A) meeting min_confidence, from an
    already-computed list of frequent itemsets (e.g. from
    brute_force_frequent_itemsets or run_apriori(...).frequent_itemsets).

    confidence(A -> B) = support(A U B) / support(A)
    lift(A -> B)       = confidence(A -> B) / support(B)

    Only itemsets of size >= 2 can produce rules (a single-item itemset
    has no non-empty proper subset to serve as an antecedent). This is a
    direct, textbook computation — no pruning shortcuts — so it is a
    trustworthy independent check against whatever rule-generation logic
    (if any) a dataset previously reported "zero rules" from.
    """
    if not (0 < min_confidence <= 1):
        raise ValueError("min_confidence must be in (0, 1]")

    support_cache: dict[frozenset[str], float] = {}

    def sup(fs: frozenset[str]) -> float:
        if fs not in support_cache:
            support_cache[fs] = _support(fs, transactions)
        return support_cache[fs]

    rules: list[AssociationRule] = []
    for itemset in frequent_itemsets:
        if len(itemset) < 2:
            continue
        items = sorted(itemset)
        for size in range(1, len(items)):
            for antecedent_tuple in combinations(items, size):
                antecedent = frozenset(antecedent_tuple)
                consequent = itemset - antecedent
                if not consequent:
                    continue
                sup_ab = sup(itemset)
                sup_a = sup(antecedent)
                sup_b = sup(consequent)
                if sup_a == 0:
                    continue
                confidence = sup_ab / sup_a
                if confidence < min_confidence:
                    continue
                lift = confidence / sup_b if sup_b > 0 else float("inf")
                rules.append(
                    AssociationRule(
                        antecedent=antecedent,
                        consequent=consequent,
                        support=sup_ab,
                        confidence=confidence,
                        lift=lift,
                    )
                )
    return rules
