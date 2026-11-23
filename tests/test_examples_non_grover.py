"""Tests for examples/ghz_ladder.py and examples/tfim_trotter.py (item 6, CPC v4 pass):
Layer A's generality on non-Grover circuits. Fast, deterministic-by-seed checks only -- these
import the example modules' building blocks directly rather than re-running the full
(several-minute) sweep each example's __main__ performs."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import ghz_ladder  # noqa: E402
import tfim_trotter  # noqa: E402

from qfim_bench.backends import SimulatorBackend  # noqa: E402


def test_ghz_circuit_has_n_minus_one_two_qubit_gates():
    for n in range(3, 7):
        qc = ghz_ladder.ghz_circuit(n)
        two_q = sum(1 for inst in qc.data if len(inst.qubits) == 2)
        assert two_q == n - 1


def test_ghz_ideal_success_is_exactly_one():
    qc = ghz_ladder.ghz_circuit(4)
    result = SimulatorBackend().run(qc, shots=8192)
    assert ghz_ladder.ghz_success(result) == pytest.approx(1.0, abs=1e-9)


def test_tfim_circuit_two_qubit_gate_count_scales_with_steps_and_n():
    qc1 = tfim_trotter.tfim_circuit(4, steps=1)
    qc2 = tfim_trotter.tfim_circuit(4, steps=2)
    g1 = sum(1 for inst in qc1.data if len(inst.qubits) == 2)
    g2 = sum(1 for inst in qc2.data if len(inst.qubits) == 2)
    assert g2 == 2 * g1 == 2 * 3  # n-1=3 RZZ gates per step at n=4


def test_tfim_ideal_return_probability_is_a_valid_probability():
    qc = tfim_trotter.tfim_circuit(4, steps=1)
    p = tfim_trotter.ideal_return_probability(qc, 4)
    assert 0.0 <= p <= 1.0


def test_tfim_return_probability_reads_the_all_zeros_count():
    class FakeResult:
        counts = {"0000": 100, "1111": 50}
        shots = 150

    assert tfim_trotter.return_probability(FakeResult(), 4) == pytest.approx(100 / 150)
