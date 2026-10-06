"""
circuit.py — Grover-based Quantum Apriori circuit construction for qfim-bench.

Implements the construction described in the companion hardware-characterization
paper (Methodology section):

    U_QA = (D . O)^r . U_init

where:
    U_init : EfficientSU2 ansatz (linear entanglement) state preparation
    O      : Hamming-weight threshold oracle, phase kickback on an ancilla in |->
    D      : diffusion operator, D = 2|psi_0><psi_0| - I

Theoretical (noiseless) success probability after r Grover iterations:

    P_r(marked) = sin^2((2r + 1) * theta),   theta = arcsin(sqrt(M / N))

M = number of oracle-marked basis states (Hamming weight >= threshold)
N = 2^n_items (total basis states, excluding ancilla)
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import asin, comb, sqrt

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import efficient_su2


# --------------------------------------------------------------------------
# Theoretical quantities (pure math, no circuit needed — useful for tests
# and for sanity-checking a hardware/simulator run against theory)
# --------------------------------------------------------------------------

def count_marked_states(n_items: int, threshold: int) -> int:
    """
    Number of n_items-bit basis states with Hamming weight >= threshold.

    M = sum_{k=threshold}^{n_items} C(n_items, k)
    """
    if not (0 <= threshold <= n_items):
        raise ValueError("threshold must be between 0 and n_items inclusive")
    return sum(comb(n_items, k) for k in range(threshold, n_items + 1))


def rotation_angle(M: int, N: int) -> float:
    """theta = arcsin(sqrt(M / N))"""
    if N <= 0:
        raise ValueError("N must be positive")
    if not (0 <= M <= N):
        raise ValueError("M must be between 0 and N inclusive")
    return asin(sqrt(M / N))


def theoretical_success_probability(M: int, N: int, r: int) -> float:
    """
    Noiseless success probability after r Grover iterations.

    P_r(marked) = sin^2((2r + 1) * theta), theta = arcsin(sqrt(M / N))

    Matches Eq. (4) in the companion paper. For M=26, N=32:
        r=1 -> 0.0508
        r=2 -> 0.3840
        r=3 -> 0.99995
        r=4 -> 0.3972
    """
    if r < 0:
        raise ValueError("r must be non-negative")
    theta = rotation_angle(M, N)
    from math import sin
    return sin((2 * r + 1) * theta) ** 2


# --------------------------------------------------------------------------
# Circuit construction
# --------------------------------------------------------------------------

INITIAL_STATES = ("ansatz", "uniform")


def bind_parameters(qc: QuantumCircuit, seed: int = 42) -> QuantumCircuit:
    """
    Bind every free parameter to a value drawn uniformly from [-pi, pi] with
    NumPy seed `seed`, in qc.parameters order. This reproduces the angle
    protocol used for the paper's hardware runs (seed 42). Returns a new,
    fully bound circuit.
    """
    if not qc.parameters:
        return qc.copy()
    np.random.seed(seed)
    values = np.random.uniform(-np.pi, np.pi, len(qc.parameters))
    return qc.assign_parameters(dict(zip(qc.parameters, values)))


def build_initial_state(
    n_items: int,
    reps: int = 1,
    kind: str = "ansatz",
    seed: int = 42,
) -> QuantumCircuit:
    """
    Initial-state preparation on n_items qubits; returns n_items + 1 qubits
    (the last is the oracle's ancilla, left untouched here).

    kind="ansatz":  EfficientSU2 (linear entanglement) with parameters bound
                    by bind_parameters(seed). This is what the paper's
                    hardware circuits used.
    kind="uniform": H on every item qubit, i.e. |psi_0> = H^{⊗n}|0>^{⊗n}.
                    This is the start state assumed by Eq. (4).
    """
    if n_items < 1:
        raise ValueError("n_items must be >= 1")
    if kind not in INITIAL_STATES:
        raise ValueError(f"kind must be one of {INITIAL_STATES}")

    qc = QuantumCircuit(n_items + 1, n_items)  # +1 ancilla, classical bits for item qubits only
    if kind == "uniform":
        qc.h(range(n_items))
        return qc

    ansatz = efficient_su2(n_items, entanglement="linear", reps=reps).decompose()
    ansatz = bind_parameters(ansatz, seed=seed)
    qc.compose(ansatz, qubits=range(n_items), inplace=True)
    return qc


def prepare_ancilla_minus(qc: QuantumCircuit, ancilla_index: int) -> None:
    """Prepare the ancilla qubit in |-> = (|0> - |1>)/sqrt(2), in place."""
    qc.x(ancilla_index)
    qc.h(ancilla_index)


def _marked_bitstrings(n_items: int, threshold: int) -> list[str]:
    """
    All n_items-bit strings (MSB-first) with Hamming weight >= threshold,
    i.e. the basis states the oracle must mark.
    """
    marked = []
    for weight in range(threshold, n_items + 1):
        for positions in combinations(range(n_items), weight):
            bits = ["0"] * n_items
            for p in positions:
                bits[p] = "1"
            marked.append("".join(bits))
    return marked


def build_oracle(n_items: int, threshold: int) -> QuantumCircuit:
    """
    Hamming-weight threshold oracle on n_items + 1 qubits (qubit n_items is
    the ancilla, assumed already prepared in |-> by the caller).

    O|b>|-> = -|b>|->  if |b| >= threshold
             |b>|->   if |b| < threshold

    Implemented by enumerating every qualifying basis state and applying a
    multi-controlled-X (targeting the ancilla) gated on that exact bit
    pattern, using X gates to flip the "0" control qubits before and after
    each multi-controlled-X (standard basis-state-marking construction).
    """
    ancilla = n_items
    qc = QuantumCircuit(n_items + 1, name="oracle")

    for bits in _marked_bitstrings(n_items, threshold):
        zero_positions = [i for i, b in enumerate(bits) if b == "0"]

        for i in zero_positions:
            qc.x(i)

        if n_items == 1:
            qc.cx(0, ancilla)
        else:
            qc.mcx(list(range(n_items)), ancilla)

        for i in zero_positions:
            qc.x(i)

    return qc


def build_diffusion(n_items: int) -> QuantumCircuit:
    """
    Diffusion operator D = 2|psi_0><psi_0| - I over the n_items item qubits,
    implemented as H^xn X^xn C^(n-1)Z X^xn H^xn. Acts only on the first
    n_items qubits; the ancilla (qubit n_items, if present in the composed
    circuit) is untouched.
    """
    qc = QuantumCircuit(n_items, name="diffusion")

    qc.h(range(n_items))
    qc.x(range(n_items))

    if n_items == 1:
        qc.z(0)
    else:
        qc.h(n_items - 1)
        qc.mcx(list(range(n_items - 1)), n_items - 1)
        qc.h(n_items - 1)

    qc.x(range(n_items))
    qc.h(range(n_items))

    return qc


@dataclass
class CircuitInfo:
    """Metadata about a built circuit, useful for scaling studies and reports."""
    n_items: int
    threshold: int
    r: int
    M: int
    N: int
    theta: float
    theoretical_p: float


def build_grover_circuit(
    n_items: int,
    threshold: int,
    r: int,
    reps: int = 1,
    measure: bool = True,
    initial_state: str = "ansatz",
    seed: int = 42,
) -> tuple[QuantumCircuit, CircuitInfo]:
    """
    Compose the full circuit: U_QA = (D . O)^r . U_init, then measure the
    n_items item qubits (ancilla is not measured).

    initial_state="ansatz" reproduces the paper's hardware circuits (bound
    EfficientSU2 start state). initial_state="uniform" uses H^{⊗n}|0>, the
    start state for which Eq. (4) is exact. The returned circuit has no free
    parameters, so it can be run directly on any backend.

    Returns (circuit, info) where info carries the theoretical quantities
    (M, N, theta, theoretical success probability) for this configuration.
    """
    if r < 0:
        raise ValueError("r must be non-negative")

    ancilla = n_items
    qc = build_initial_state(n_items, reps=reps, kind=initial_state, seed=seed)
    prepare_ancilla_minus(qc, ancilla)

    oracle = build_oracle(n_items, threshold)
    diffusion = build_diffusion(n_items)

    for _ in range(r):
        qc.compose(oracle, qubits=range(n_items + 1), inplace=True)
        qc.compose(diffusion, qubits=range(n_items), inplace=True)

    if measure:
        qc.measure(range(n_items), range(n_items))

    M = count_marked_states(n_items, threshold)
    N = 2 ** n_items
    theta = rotation_angle(M, N)
    info = CircuitInfo(
        n_items=n_items,
        threshold=threshold,
        r=r,
        M=M,
        N=N,
        theta=theta,
        theoretical_p=theoretical_success_probability(M, N, r),
    )
    return qc, info
