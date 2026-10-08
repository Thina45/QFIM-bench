"""
encoding.py: the single place that defines how itemsets map to qubits and bitstrings.

Convention (one rule, used by the oracle, the encoder, the decoder and post-processing):

    item_order[p]  <->  qubit p  <->  bit p of the basis-state index

A basis state is identified by the integer index i = sum_p 2^p [item_order[p] in itemset].
Qiskit prints a measured count key as the binary form of i with qubit n-1 leftmost and qubit 0
rightmost, so `encode_itemset_to_bitstring` returns exactly the key Qiskit would report for that
itemset, and `decode_bitstring_to_itemset` inverts it.

(Before v1.0.2 the decoder read the key left to right as item_order[0..n-1], which reversed the
item/qubit mapping. The symmetric Hamming-weight oracle hid this; asymmetric marking does not.
See review/AUDIT.md item 4 and tests/test_ordering.py.)
"""

from __future__ import annotations


def itemset_to_index(itemset: set[str], item_order: list[str]) -> int:
    """Basis-state index of an itemset: bit p is set iff item_order[p] is in the itemset."""
    unknown = set(itemset) - set(item_order)
    if unknown:
        raise ValueError(f"itemset contains items not in item_order: {unknown}")
    return sum(1 << p for p, item in enumerate(item_order) if item in itemset)


def index_to_itemset(index: int, item_order: list[str]) -> set[str]:
    """Inverse of itemset_to_index."""
    n = len(item_order)
    if not (0 <= index < 2**n):
        raise ValueError(f"index {index} out of range for {n} items")
    return {item for p, item in enumerate(item_order) if (index >> p) & 1}


def encode_itemset_to_bitstring(itemset: set[str], item_order: list[str]) -> str:
    """
    The count key Qiskit reports when exactly this itemset is measured. With
    item_order=["eggs","milk","bread"], {"eggs"} gives "001" (qubit 0 is the rightmost
    character) and {"milk"} gives "010".

    Raises ValueError if itemset contains an item not in item_order, since that indicates a
    mismatch between the selected-items universe and whatever produced the itemset.
    """
    return format(itemset_to_index(itemset, item_order), f"0{len(item_order)}b")


def decode_bitstring_to_itemset(bits: str, item_order: list[str]) -> set[str]:
    """Inverse of encode_itemset_to_bitstring: Qiskit count key -> itemset."""
    if len(bits) != len(item_order):
        raise ValueError(
            f"bitstring length {len(bits)} does not match item_order length {len(item_order)}"
        )
    return index_to_itemset(int(bits, 2), item_order)


def all_nonempty_subsets(item_order: list[str]) -> list[set[str]]:
    """
    Every non-empty subset of item_order, i.e. the full 2^m - 1 candidate itemset space the
    circuit searches over. Used by postprocessing.py to score every candidate against the
    measured distribution, and by classical.py's brute-force ground truth for small item counts.
    """
    from itertools import combinations

    subsets = []
    for size in range(1, len(item_order) + 1):
        for combo in combinations(item_order, size):
            subsets.append(set(combo))
    return subsets
