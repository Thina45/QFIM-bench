"""
marking.py: choosing which basis states the oracle marks.

The marked set is PRECOMPUTED CLASSICALLY. That is the standard oracle model for Grover search
over a database predicate, and it has a consequence worth stating plainly: by the time the marked
set is known, the mining problem is already solved classically, so this pipeline demonstrates and
benchmarks the quantum search step; it does not offer an advantage. A real oracle that evaluates
support on the fly would need data access (O(T) classical time per query, or QRAM).

Three ways to mark states (QFIMConfig.marking):

    "support"      mark every non-empty itemset whose classical support is >= min_support
                   (data-driven; the primary path)
    "cardinality"  mark every itemset of size >= oracle_threshold (the v1 oracle; independent of
                   the data, see analysis/data_independence.py)
    "explicit"     mark exactly the given basis-state indices (benchmarks with a chosen M)

The empty itemset has support 1 by definition. It is excluded here because it is not an itemset
of interest; its basis state (index 0) is therefore never marked by "support".
"""

from __future__ import annotations

from .classical import brute_force_frequent_itemsets
from .encoding import itemset_to_index


def data_driven_marked_states(
    transactions: list[set[str]], item_order: list[str], min_support: float
) -> list[int]:
    """
    Basis-state indices (encoding.py convention) of every non-empty itemset over `item_order`
    with classical support >= min_support in `transactions`.

    Raises ValueError if no itemset is frequent: Grover search needs at least one marked state.
    """
    frequent = brute_force_frequent_itemsets(transactions, min_support)
    indices = sorted(itemset_to_index(set(fs), item_order) for fs in frequent)
    if not indices:
        raise ValueError(
            f"no itemset has support >= {min_support}; lower min_support (nothing to mark)"
        )
    return indices
