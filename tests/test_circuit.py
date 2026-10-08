"""Circuit construction and theory checks.

Numeric tolerances for sampled values are derived from shot noise (5 binomial standard errors),
not chosen ad hoc. Exact statevector checks use a numerical tolerance of 1e-9.
"""

import math

import numpy as np
import pytest
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from qfim_bench.circuit import (
    build_grover_circuit,
    build_oracle,
    build_oracle_for_states,
    cardinality_marked_indices,
    count_marked_states,
    exact_success_probability,
    optimal_iterations,
    success_probability_from_start,
    theoretical_success_probability,
)

SHOTS = 8192


def five_sigma(p: float, shots: int = SHOTS) -> float:
    """5 standard errors of a binomial proportion, with a floor so p ~ 0 or 1 stays testable."""
    return max(5.0 * math.sqrt(p * (1.0 - p) / shots), 1e-3)


def sampled_marked_fraction(qc, info, seed=42) -> float:
    counts = AerSimulator(seed_simulator=seed).run(qc, shots=SHOTS).result().get_counts()
    marked = {format(i, f"0{info.n_items}b") for i in info.marked_indices}
    return sum(v for k, v in counts.items() if k in marked) / SHOTS


# ---------------------------------------------------------------- closed-form theory

def test_theoretical_probability_matches_paper():
    # M=26, N=32 (5 items, t=2): values reported in the paper's Table 2
    assert abs(theoretical_success_probability(26, 32, 1) - 0.0508) < 0.001
    assert abs(theoretical_success_probability(26, 32, 2) - 0.3840) < 0.001
    assert abs(theoretical_success_probability(26, 32, 3) - 0.99995) < 0.001
    assert abs(theoretical_success_probability(26, 32, 4) - 0.3972) < 0.001
    assert theoretical_success_probability(26, 32, 0) == pytest.approx(26 / 32)


def test_marked_state_count():
    assert count_marked_states(5, 2) == 26
    assert count_marked_states(5, 0) == 32
    assert count_marked_states(3, 3) == 1


# Reference values from the experiment plan (N = 32), verified by statevector below.
SPARSE_TABLE = {
    1: (4, [0.0313, 0.2583, 0.6024, 0.8969, 0.9992, 0.8596]),
    2: (3, [0.0625, 0.4727, 0.9084, 0.9613, 0.5817]),
    3: (2, [0.0938, 0.6460, 0.9998, 0.6742]),
    4: (2, [0.1250, 0.7813, 0.9453, 0.3301]),
}


# The reference table is rounded to 4 decimals, so each entry carries up to 5e-5 of rounding error
# (e.g. 1/32 = 0.03125 is printed 0.0313); the tolerance below is that error plus float slack.
ROUNDING_TOL = 6e-5


@pytest.mark.parametrize("M", [1, 2, 3, 4])
def test_sparse_marking_reference_table(M):
    r_opt, expected = SPARSE_TABLE[M]
    assert optimal_iterations(M, 32) == r_opt
    for r, p in enumerate(expected):
        assert theoretical_success_probability(M, 32, r) == pytest.approx(p, abs=ROUNDING_TOL)
        exact = exact_success_probability(5, 2, r, initial_state="uniform", marked_states=list(range(M)))
        assert exact == pytest.approx(p, abs=ROUNDING_TOL)


def test_degenerate_regime_r_opt_is_zero():
    """At M=26 of 32, doing nothing already succeeds with 0.8125: r_opt is 0 and r=2 is worse than r=0."""
    assert optimal_iterations(26, 32) == 0
    assert theoretical_success_probability(26, 32, 2) < theoretical_success_probability(26, 32, 0)


# ---------------------------------------------------------------- oracles

def test_state_oracle_equals_cardinality_oracle_as_operators():
    expected = Operator(build_oracle(5, 2)).data
    got = Operator(build_oracle_for_states(5, cardinality_marked_indices(5, 2))).data
    assert np.allclose(expected, got)


def test_oracle_validation():
    with pytest.raises(ValueError):
        build_oracle_for_states(3, [])
    with pytest.raises(ValueError):
        build_oracle_for_states(3, [1, 1])
    with pytest.raises(ValueError):
        build_oracle_for_states(3, [8])


# ---------------------------------------------------------------- circuit structure

def test_built_circuit_has_no_free_parameters():
    for init in ("ansatz", "uniform"):
        for diffusion in ("matched", "hadamard"):
            qc, _ = build_grover_circuit(5, 2, 2, initial_state=init, diffusion=diffusion)
            assert len(qc.parameters) == 0


def test_invalid_options_rejected():
    with pytest.raises(ValueError):
        build_grover_circuit(5, 2, 1, initial_state="bogus")
    with pytest.raises(ValueError):
        build_grover_circuit(5, 2, 1, diffusion="bogus")


# ---------------------------------------------------------------- uniform start

@pytest.mark.parametrize("r", [1, 2, 3, 4])
def test_uniform_start_matches_theory_exactly(r):
    exact = exact_success_probability(5, 2, r, initial_state="uniform")
    assert exact == pytest.approx(theoretical_success_probability(26, 32, r), abs=1e-9)


@pytest.mark.parametrize("r", [1, 2, 3, 4])
def test_uniform_start_sampled_within_five_sigma(r):
    qc, info = build_grover_circuit(5, 2, r, initial_state="uniform")
    empirical = sampled_marked_fraction(qc, info)
    assert abs(empirical - info.theoretical_p) < five_sigma(info.theoretical_p)


# ---------------------------------------------------------------- ansatz start: the pitfall and its fix

@pytest.mark.parametrize("seed", [0, 1, 7, 42, 123])
@pytest.mark.parametrize("r", [0, 1, 2, 3])
def test_matched_diffusion_follows_grover_formula_from_ansatz(seed, r):
    """With a diffusion matched to the ansatz, P_r = sin^2((2r+1) theta_A), theta_A = asin(sqrt(P_A))."""
    qc, info = build_grover_circuit(5, 2, r, initial_state="ansatz", diffusion="matched", seed=seed, measure=False)
    exact = exact_success_probability(5, 2, r, initial_state="ansatz", diffusion="matched", seed=seed)
    assert exact == pytest.approx(success_probability_from_start(info.start_marked_probability, r), abs=1e-9)
    assert info.theoretical_p == pytest.approx(exact, abs=1e-9)


def test_mismatched_hadamard_diffusion_keeps_ansatz_flat_v1_values():
    """The v1 ansatz circuits used the Hadamard diffusion. Exact values at seed 42, M=26 (pinned):
    flat at 0.80-0.82 for every r, with no amplification."""
    expected = [0.8087, 0.8000, 0.8215, 0.8208, 0.7996]
    for r, p in enumerate(expected):
        got = exact_success_probability(5, 2, r, initial_state="ansatz", diffusion="hadamard", seed=42)
        assert got == pytest.approx(p, abs=1e-4)


def test_mismatched_diffusion_has_no_closed_form():
    _, info = build_grover_circuit(5, 2, 2, initial_state="ansatz", diffusion="hadamard")
    assert math.isnan(info.theoretical_p)


def test_matched_diffusion_removes_flatness():
    """The pitfall in one assertion: same start state and oracle, only the diffusion differs, and the
    matched curve reaches (almost) 1 at r=3 where the mismatched one stays near 0.8."""
    matched = exact_success_probability(5, 2, 3, initial_state="ansatz", diffusion="matched", seed=42)
    mismatched = exact_success_probability(5, 2, 3, initial_state="ansatz", diffusion="hadamard", seed=42)
    assert matched > 0.99
    assert mismatched < 0.85
