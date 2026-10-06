"""
preprocessing.py — Stage 1 of the qfim-bench pipeline: classical
transactional preprocessing and frequency-based item selection.

Matches the companion paper's description: items are selected classically
by frequency ranking over the full dataset, before any quantum circuit is
constructed. The quantum side never sees the full item universe — only the
top_k_items selected here.

Expects a "basket-style" CSV: one row per transaction, one column per item
slot (items present in that transaction), with ragged rows allowed (missing
slots as empty cells) — this matches common basket-analysis dataset formats
(e.g. the Kaggle grocery-store dataset used in the companion paper), not a
one-hot/wide matrix.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass


def load_transactions(path: str) -> list[set[str]]:
    """
    Load a basket-style CSV (one row per transaction, item names across
    columns, ragged rows allowed — different transactions may have
    different numbers of items) into a list of transactions, each a set
    of item names with blank cells dropped.

    Deliberately uses Python's csv module rather than pandas.read_csv:
    pandas' C parser infers a fixed column count from the first row and
    raises a ParserError on ragged rows (verified directly — a dataset
    where transaction lengths vary, which basket-style data always does,
    fails to load with pandas' default reader). Returns a list rather
    than a DataFrame for the same reason: ragged transactions don't fit a
    rectangular table, and downstream code (item selection, encoding,
    classical baselines) all want "list of item-sets" as their native
    input shape anyway.
    """
    transactions = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            items = {cell.strip() for cell in row if cell.strip() != ""}
            transactions.append(items)
    return transactions


@dataclass
class ItemFrequency:
    item: str
    count: int
    support: float


def rank_items_by_frequency(transactions: list[set[str]]) -> list[ItemFrequency]:
    """
    Count how many transactions contain each item, and return items sorted
    by descending frequency (ties broken alphabetically for determinism —
    important for reproducibility, since an unstable sort would make
    top-k selection non-deterministic when items tie on count).
    """
    if not transactions:
        raise ValueError("transactions must be a non-empty list")

    counts: dict[str, int] = {}
    for t in transactions:
        for item in t:
            counts[item] = counts.get(item, 0) + 1

    n = len(transactions)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [ItemFrequency(item=item, count=c, support=c / n) for item, c in ranked]


def select_top_k_items(transactions: list[set[str]], k: int) -> list[str]:
    """
    Classically select the k most frequent items across the full dataset,
    by frequency ranking (companion paper: "selected classically by
    frequency ranking over the full dataset prior to any quantum circuit
    construction"). Returns item names in descending-frequency order —
    this order is also used later as the fixed item-to-qubit ordering in
    encoding.py, so it must be deterministic.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    ranked = rank_items_by_frequency(transactions)
    if k > len(ranked):
        raise ValueError(
            f"Requested top_k_items={k} but dataset only has {len(ranked)} distinct items"
        )
    return [r.item for r in ranked[:k]]


def reduce_to_selected_items(
    transactions: list[set[str]], selected_items: list[str]
) -> list[set[str]]:
    """
    Reduce every transaction to only the selected items, and drop
    transactions that end up empty (contain none of the selected items) —
    matching the companion paper's exact derivation of its 4,593-transaction
    quantum-experiment subset from the full 7,501-transaction dataset.
    """
    selected = set(selected_items)
    reduced = [t & selected for t in transactions]
    return [t for t in reduced if t]
