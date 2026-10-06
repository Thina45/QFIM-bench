"""Circuit construction and theory checks (paper Eq. 4 and the M=26, N=32 configuration)."""

import pytest
from qiskit_aer import AerSimulator

from qfim_bench.circuit import (
    build_grover_circuit,
    count_marked_states,
    theoretical_success_probability,
)


def test_theoretical_probability_matches_paper():
    # M=26, N=32 (5 items, t=2): values reported in the paper's Table III
    assert abs(theoretical_success_probability(26, 32, 1) - 0.0508) < 0.001
    assert abs(theoretical_success_probability(26, 32, 2) - 0.3840) < 0.001
    assert abs(theoretical_success_probability(26, 32, 3) - 0.99995) < 0.001
    assert abs(theoretical_success_probability(26, 32, 4) - 0.3972) < 0.001


def test_marked_state_count():
    assert count_marked_states(5, 2) == 26
    assert count_marked_states(5, 0) == 32
    assert count_marked_states(3, 3) == 1


def test_built_circuit_has_no_free_parameters():
    for init in ("ansatz", "uniform"):
        qc, _ = build_grover_circuit(5, 2, 2, initial_state=init)
        assert len(qc.parameters) == 0


def test_invalid_initial_state_rejected():
    with pytest.raises(ValueError):
        build_grover_circuit(5, 2, 1, initial_state="bogus")


@pytest.mark.parametrize("r", [1, 2, 3, 4])
def test_uniform_start_matches_theory_noiselessly(r):
    """With the uniform H^n start state assumed by Eq. (4), the noiseless
    simulator reproduces the theoretical success probability within shot noise
    (8192 shots: sd < 0.006, tolerance 0.03 = 5 sd)."""
    qc, info = build_grover_circuit(5, 2, r, initial_state="uniform")
    counts = AerSimulator(seed_simulator=42).run(qc, shots=8192).result().get_counts()
    empirical = sum(v for k, v in counts.items() if k.count("1") >= 2) / 8192
    assert abs(empirical - info.theoretical_p) < 0.03


def test_ansatz_start_is_not_the_eq4_regime():
    """Documents a finding: the paper's random-ansatz start state does NOT follow
    the oscillatory Eq. (4) curve even without noise (empirical ~0.80 at every r)."""
    values = []
    for r in (1, 2, 3, 4):
        qc, _ = build_grover_circuit(5, 2, r, initial_state="ansatz", seed=42)
        counts = AerSimulator(seed_simulator=42).run(qc, shots=8192).result().get_counts()
        values.append(sum(v for k, v in counts.items() if k.count("1") >= 2) / 8192)
    assert all(0.75 < v < 0.86 for v in values)
    assert max(values) - min(values) < 0.05
