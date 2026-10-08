"""Oracle synthesis variants: same unitary on the item register, different width and cost."""

import pytest

from qfim_bench.circuit import (
    ORACLE_STYLES,
    build_grover_circuit,
    build_oracle_variant,
    exact_success_probability,
    oracle_width,
    theoretical_success_probability,
)


def _weight2(n, m):
    return [i for i in range(2**n) if bin(i).count("1") == 2][:m]


@pytest.mark.parametrize("style", ORACLE_STYLES)
@pytest.mark.parametrize("n,m", [(2, 1), (3, 1), (4, 2), (5, 4)])
def test_every_style_follows_the_analytical_curve(style, n, m):
    for r in range(0, 4):
        p = exact_success_probability(n, 0, r, initial_state="uniform",
                                      marked_states=_weight2(n, m), oracle_style=style)
        assert p == pytest.approx(theoretical_success_probability(m, 2**n, r), abs=1e-9)


@pytest.mark.parametrize("style", ORACLE_STYLES)
def test_asymmetric_marked_set_is_marked_exactly(style):
    """Non-weight-symmetric set, so a wrong control pattern or reversed bit order would show up."""
    marked = [1, 6, 11]
    p = exact_success_probability(4, 0, 1, initial_state="uniform", marked_states=marked, oracle_style=style)
    assert p == pytest.approx(theoretical_success_probability(3, 16, 1), abs=1e-9)


def test_widths():
    assert oracle_width(5, "mcx") == 6
    assert oracle_width(5, "mcz") == 5
    assert oracle_width(5, "mcx_vchain") == 9
    assert oracle_width(2, "mcx_vchain") == 3


def test_default_style_is_the_reference_oracle():
    qc, info = build_grover_circuit(5, 0, 1, initial_state="uniform", marked_states=[3])
    assert info.oracle_style == "mcx"
    assert qc.num_qubits == 6


def test_mcz_circuit_has_no_ancilla():
    qc, _ = build_grover_circuit(4, 0, 1, initial_state="uniform", marked_states=[3], oracle_style="mcz")
    assert qc.num_qubits == 4


def test_unknown_style_rejected():
    with pytest.raises(ValueError):
        build_grover_circuit(3, 0, 1, marked_states=[3], oracle_style="nope")
    with pytest.raises(ValueError):
        build_oracle_variant(3, [3], "nope")
