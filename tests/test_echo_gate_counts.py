"""The depth-matched echo circuit should carry about twice the two-qubit gates of its ladder circuit."""

import pytest
from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

from qfim_bench.backends import HardwareBackend
from qfim_bench.circuit import build_grover_circuit, optimal_iterations

LADDER = [(3, 1), (4, 2), (5, 4)]


def _marked(n, M):
    return [i for i in range(2**n) if bin(i).count("1") == 2][:M]


def echo(n, M, r):
    body, _ = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=_marked(n, M),
                                   oracle_style="mcz", measure=False)
    qc = QuantumCircuit(body.num_qubits, n)
    qc.compose(body, inplace=True)
    qc.barrier()
    qc.compose(body.inverse(), inplace=True)
    qc.measure(range(n), range(n))
    return qc


@pytest.mark.parametrize("n,M", LADDER)
def test_echo_has_about_twice_the_two_qubit_gates(n, M, monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    r = optimal_iterations(M, 2**n)
    ladder, _ = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=_marked(n, M), oracle_style="mcz")
    hb = HardwareBackend(dry_run=True)  # same transpile settings as hardware (opt level 3, seed 42), FakeMarrakesh target
    hb.run_batch([ladder, echo(n, M, r)], shots=8192)
    g_ladder, g_echo = (c["two_qubit_gates"] for c in hb.last_report["circuits"])
    print(f"n={n} M={M} r={r}: ladder 2Q={g_ladder}, echo 2Q={g_echo}, ratio={g_echo / g_ladder:.3f}")
    assert g_echo / g_ladder == pytest.approx(2.0, rel=0.20)
