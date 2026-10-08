"""Bit-ordering regression tests (AUDIT item 4; fixed in v1.0.2).

Convention (encoding.py): item_order[p] <-> qubit p <-> bit p of the basis-state index. Qiskit
count keys print qubit 0 as the rightmost character. The Hamming-weight oracle is permutation
symmetric, so a reversed mapping is invisible in the original experiments; these tests exercise
the mapping directly, on every qubit (the middle qubit of 5 is a fixed point of reversal, so a
single-qubit test on it would miss the bug).
"""

import pytest
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from qfim_bench.encoding import (
    decode_bitstring_to_itemset,
    encode_itemset_to_bitstring,
    index_to_itemset,
    itemset_to_index,
)

ORDER = [f"item_{i}" for i in range(5)]


def _count_key_for_flipped_qubit(qubit: int) -> str:
    qc = QuantumCircuit(5, 5)
    qc.x(qubit)
    qc.measure(range(5), range(5))
    counts = AerSimulator(seed_simulator=1).run(qc, shots=64).result().get_counts()
    assert len(counts) == 1
    return next(iter(counts))


def test_qiskit_count_key_is_little_endian():
    """Pins the Qiskit convention this package relies on."""
    assert _count_key_for_flipped_qubit(0) == "00001"
    assert _count_key_for_flipped_qubit(4) == "10000"


@pytest.mark.parametrize("qubit", range(5))
def test_flipped_qubit_decodes_to_matching_item(qubit):
    key = _count_key_for_flipped_qubit(qubit)
    assert decode_bitstring_to_itemset(key, ORDER) == {ORDER[qubit]}


@pytest.mark.parametrize("qubit", range(5))
def test_encode_matches_what_qiskit_reports(qubit):
    assert encode_itemset_to_bitstring({ORDER[qubit]}, ORDER) == _count_key_for_flipped_qubit(qubit)


def test_index_round_trip_all_itemsets():
    for index in range(2**5):
        assert itemset_to_index(index_to_itemset(index, ORDER), ORDER) == index


def test_unknown_item_rejected():
    with pytest.raises(ValueError):
        itemset_to_index({"not_an_item"}, ORDER)
