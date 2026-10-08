"""Bit-ordering regression tests (AUDIT item 4).

Convention in the oracle and in encode_itemset_to_bitstring: item_order[p] <-> qubit p.
Qiskit count strings print clbit 0 as the RIGHTMOST character, so qubit p appears at
string index n-1-p. decode_bitstring_to_itemset currently maps string index p to
item_order[p], i.e. it reverses the convention.

The Hamming-weight oracle is permutation symmetric, so the reversal has no effect on any
success probability reported so far. It becomes live as soon as marking or labelling is
asymmetric, which is why this test is kept even though the symmetric experiments are
unaffected.
"""

import pytest
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from qfim_bench.encoding import decode_bitstring_to_itemset

ORDER = [f"item_{i}" for i in range(5)]


def _count_key_for_flipped_qubit(qubit: int) -> str:
    qc = QuantumCircuit(5, 5)
    qc.x(qubit)
    qc.measure(range(5), range(5))
    counts = AerSimulator(seed_simulator=1).run(qc, shots=64).result().get_counts()
    assert len(counts) == 1
    return next(iter(counts))


def test_qiskit_count_key_is_little_endian():
    """Pins the Qiskit convention this package relies on: flipping qubit 0 sets the last character."""
    assert _count_key_for_flipped_qubit(0) == "00001"
    assert _count_key_for_flipped_qubit(4) == "10000"


_REVERSAL = pytest.mark.xfail(
    strict=True,
    reason="AUDIT item 4: decode maps string index p to item_order[p]; qubit p sits at index n-1-p. "
    "Fix after Phase 1 approval, then remove this marker.",
)


@pytest.mark.parametrize(
    "qubit",
    # With 5 qubits the middle index maps to itself under reversal, so qubit 2 is unaffected.
    [pytest.param(q, marks=_REVERSAL) if q != 2 else q for q in range(5)],
)
def test_flipped_qubit_decodes_to_matching_item(qubit):
    key = _count_key_for_flipped_qubit(qubit)
    assert decode_bitstring_to_itemset(key, ORDER) == {ORDER[qubit]}
