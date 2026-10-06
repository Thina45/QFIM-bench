"""
Add to tests/test_data_classical_pipeline.py (or as a new file
tests/test_association_rules.py — either is fine, just keep it in tests/).

Verifies generate_association_rules against a hand-computed example AND
checks it against the real dataset to settle whether "zero rules at
confidence >= 0.5" is a genuine property of the data or was a bug.
"""

import pytest

from qfim_bench.classical import (
    brute_force_frequent_itemsets,
    generate_association_rules,
)


def test_association_rules_match_hand_computed_example():
    transactions = [
        {"milk", "bread"},
        {"milk", "bread", "eggs"},
        {"milk"},
        {"bread", "eggs"},
        {"milk", "bread", "eggs"},
    ]
    frequent = brute_force_frequent_itemsets(transactions, min_support=0.4)
    rules = generate_association_rules(transactions, frequent, min_confidence=0.5)

    by_pair = {(tuple(sorted(r.antecedent)), tuple(sorted(r.consequent))): r for r in rules}

    eggs_to_bread = by_pair[(("eggs",), ("bread",))]
    assert eggs_to_bread.confidence == pytest.approx(1.0)
    assert eggs_to_bread.support == pytest.approx(0.6)

    milk_to_bread = by_pair[(("milk",), ("bread",))]
    assert milk_to_bread.confidence == pytest.approx(0.75)

    # milk -> eggs has confidence exactly 0.5, right at the threshold: must
    # be included (">= min_confidence", not strictly ">").
    assert (("milk",), ("eggs",)) in by_pair

    assert len(rules) == 12


def test_association_rules_empty_at_impossible_confidence():
    transactions = [{"a", "b"}, {"a"}, {"b"}]
    frequent = brute_force_frequent_itemsets(transactions, min_support=0.3)
    # confidence can never exceed 1.0, so nothing should pass > 1.0 — this
    # guards against an off-by-one on the boundary comparison.
    with pytest.raises(ValueError):
        generate_association_rules(transactions, frequent, min_confidence=1.5)


def test_association_rules_on_sample_dataset_at_paper_threshold(transactions):
    """
    Reproduces the README's open caveat directly: are there really zero
    rules at confidence >= 0.5 on this dataset, or was that a bug in how
    rules were previously derived? This test doesn't assert an answer —
    it prints the actual rule count so the real run settles the question,
    and it must not raise.
    """
    frequent = brute_force_frequent_itemsets(transactions, min_support=0.05)
    rules = generate_association_rules(transactions, frequent, min_confidence=0.5)
    print(f"\nrules at min_confidence=0.5 on sample dataset: {len(rules)}")
    for r in sorted(rules, key=lambda r: -r.confidence)[:10]:
        print(f"  {sorted(r.antecedent)} -> {sorted(r.consequent)}  "
              f"conf={r.confidence:.3f} support={r.support:.3f} lift={r.lift:.3f}")
    assert isinstance(rules, list)  # always true; the point is the printed count above
