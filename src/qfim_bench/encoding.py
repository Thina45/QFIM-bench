"""
encoding.py — Stage 2 of the qfim-bench pipeline: item <-> qubit binary
encoding.

Each computational basis state |b> = |b_1...b_m> of an m-qubit register
represents an itemset X_b = {item_k : b_k = 1}; Hamming weight |b| = |X_b|
(companion paper, Methodology -> Quantum State Encoding).

The item order used here (typically select_top_k_items()'s output order,
descending frequency) is the single source of truth for which qubit
corresponds to which item, and must be passed consistently to every
encode/decode call across the pipeline — encoding.py does not store or
infer this order itself, to keep it a stateless, easily-testable module.
"""

from __future__ import annotations


def encode_itemset_to_bitstring(itemset: set[str], item_order: list[str]) -> str:
    """
    Encode an itemset as an MSB-first bitstring over item_order, e.g. with
    item_order=["eggs","milk","bread"] and itemset={"milk"}, returns "010".

    Raises ValueError if itemset contains an item not in item_order, since
    that indicates a mismatch between the selected-items universe and
    whatever produced this itemset (a bug worth surfacing immediately,
    not silently ignoring).
    """
    unknown = itemset - set(item_order)
    if unknown:
        raise ValueError(f"itemset contains items not in item_order: {unknown}")
    return "".join("1" if item in itemset else "0" for item in item_order)


def decode_bitstring_to_itemset(bits: str, item_order: list[str]) -> set[str]:
    """
    Inverse of encode_itemset_to_bitstring: given an MSB-first bitstring
    and the same item_order used to encode it, returns the itemset it
    represents.
    """
    if len(bits) != len(item_order):
        raise ValueError(
            f"bitstring length {len(bits)} does not match item_order length {len(item_order)}"
        )
    return {item for bit, item in zip(bits, item_order) if bit == "1"}


def all_nonempty_subsets(item_order: list[str]) -> list[set[str]]:
    """
    Every non-empty subset of item_order, i.e. the full 2^m - 1 candidate
    itemset space the quantum circuit searches over (companion paper:
    "2^5 - 1 = 31 non-empty candidate itemsets"). Used by
    postprocessing.py to score every candidate against the measured
    distribution, and by classical.py's brute-force ground-truth
    computation for small item counts.
    """
    from itertools import combinations

    subsets = []
    for size in range(1, len(item_order) + 1):
        for combo in combinations(item_order, size):
            subsets.append(set(combo))
    return subsets
