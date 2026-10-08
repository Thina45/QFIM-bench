"""
circuit.py: Grover-based frequent-itemset search circuits for qfim-bench.

What this circuit is, exactly: a one-shot Grover search over all 2^n candidate itemsets. A set of
basis states is marked by an oracle that is *precomputed classically* (from classical support, from
a Hamming-weight rule, or given explicitly); Grover iterations then amplify that set and the
measured bitstrings are scored classically. It is not level-wise Apriori (no downward-closure
pruning, no quantum support evaluation), and it carries no claim of quantum advantage: classically
precomputing the marked set already solves the mining problem.

    U = (D . O)^r . A

    A : start-state preparation (H^n, or a bound EfficientSU2 ansatz)
    O : oracle, phase kickback on an ancilla in |->, one multi-controlled X per marked state
    D : diffusion, a reflection about the start state A|0>

Grover theory requires D to reflect about the SAME state the iteration starts from:

    diffusion="matched"   D = A (2|0><0| - I) A^dagger     (correct for any start state)
    diffusion="hadamard"  D = H^n (2|0><0| - I) H^n        (reflection about the uniform state)

The two coincide for the uniform start. For the ansatz start, "hadamard" is MISMATCHED: it does not
amplify the marked subspace, and the success probability stays flat. The v1 paper's ansatz
experiments used the mismatched operator; it is kept (and labelled) so that pitfall stays
reproducible. See review/AUDIT.md.

With a matched diffusion, the noiseless success probability after r iterations is

    P_r = sin^2((2r + 1) theta),   theta = arcsin(sqrt(P_0)),   P_0 = P(marked | start state)

P_0 = M/N for the uniform start. For the mismatched case there is no closed form
(CircuitInfo.theoretical_p is NaN); use exact_success_probability() instead.

Qubit/bit convention: see encoding.py (item_order[p] <-> qubit p <-> bit p of the basis index).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from math import asin, comb, floor, nan, pi, sin, sqrt
from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import efficient_su2
from qiskit.quantum_info import Statevector


# --------------------------------------------------------------------------
# Theoretical quantities (pure math, no circuit needed)
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
    Noiseless success probability after r Grover iterations from the uniform start with a matched
    diffusion: P_r = sin^2((2r + 1) theta), theta = arcsin(sqrt(M / N)).

    For M=26, N=32: r=1 -> 0.0508, r=2 -> 0.3840, r=3 -> 0.99995, r=4 -> 0.3972.
    """
    if r < 0:
        raise ValueError("r must be non-negative")
    return sin((2 * r + 1) * rotation_angle(M, N)) ** 2


def success_probability_from_start(p_start: float, r: int) -> float:
    """P_r = sin^2((2r + 1) asin(sqrt(p_start))): Grover with a matched diffusion from any start state."""
    if r < 0:
        raise ValueError("r must be non-negative")
    if not (0.0 <= p_start <= 1.0):
        raise ValueError("p_start must be in [0, 1]")
    return sin((2 * r + 1) * asin(sqrt(p_start))) ** 2


def optimal_iterations(M: int, N: int) -> int:
    """r_opt = floor(pi / (4 theta)). Requires M, the number of marked states, to be known."""
    if M < 1:
        raise ValueError("M must be at least 1")
    return floor(pi / (4.0 * rotation_angle(M, N)))


# --------------------------------------------------------------------------
# Start-state preparation
# --------------------------------------------------------------------------

INITIAL_STATES = ("ansatz", "uniform")
DIFFUSIONS = ("matched", "hadamard")


def bind_parameters(qc: QuantumCircuit, seed: int = 42) -> QuantumCircuit:
    """
    Bind every free parameter to a value drawn uniformly from [-pi, pi] with NumPy seed `seed`, in
    qc.parameters order (the angle protocol of the paper's hardware runs, seed 42). Returns a new,
    fully bound circuit.
    """
    if not qc.parameters:
        return qc.copy()
    np.random.seed(seed)
    values = np.random.uniform(-np.pi, np.pi, len(qc.parameters))
    return qc.assign_parameters(dict(zip(qc.parameters, values)))


def build_start_preparation(
    n_items: int, reps: int = 1, kind: str = "ansatz", seed: int = 42
) -> QuantumCircuit:
    """
    The start-state unitary A on n_items qubits (no ancilla).

    kind="uniform": H on every qubit.
    kind="ansatz":  EfficientSU2 (linear entanglement, `reps` repetitions) with parameters bound
                    by bind_parameters(seed).
    """
    if n_items < 1:
        raise ValueError("n_items must be >= 1")
    if kind not in INITIAL_STATES:
        raise ValueError(f"kind must be one of {INITIAL_STATES}")
    if kind == "uniform":
        qc = QuantumCircuit(n_items, name="A_uniform")
        qc.h(range(n_items))
        return qc
    ansatz = efficient_su2(n_items, entanglement="linear", reps=reps).decompose()
    return bind_parameters(ansatz, seed=seed)


def build_initial_state(
    n_items: int,
    reps: int = 1,
    kind: str = "ansatz",
    seed: int = 42,
) -> QuantumCircuit:
    """
    The start state on n_items + 1 qubits (the last is the oracle's ancilla, left untouched) with
    classical bits for the item qubits only.
    """
    prep = build_start_preparation(n_items, reps=reps, kind=kind, seed=seed)
    qc = QuantumCircuit(n_items + 1, n_items)
    qc.compose(prep, qubits=range(n_items), inplace=True)
    return qc


def start_marked_probability(preparation: QuantumCircuit, marked_indices: Sequence[int]) -> float:
    """P_0 = P(marked | A|0>), from the exact statevector of the preparation."""
    probs = Statevector.from_instruction(preparation).probabilities()
    return float(sum(probs[i] for i in marked_indices))


def prepare_ancilla_minus(qc: QuantumCircuit, ancilla_index: int) -> None:
    """Prepare the ancilla qubit in |-> = (|0> - |1>)/sqrt(2), in place."""
    qc.x(ancilla_index)
    qc.h(ancilla_index)


# --------------------------------------------------------------------------
# Oracles
# --------------------------------------------------------------------------

def cardinality_marked_indices(n_items: int, threshold: int) -> list[int]:
    """Basis-state indices with Hamming weight >= threshold (the v1 cardinality oracle's marked set)."""
    count_marked_states(n_items, threshold)  # validates the arguments
    return [i for i in range(2**n_items) if bin(i).count("1") >= threshold]


def _marked_bitstrings(n_items: int, threshold: int) -> list[str]:
    """
    All n_items-bit patterns (string index p <-> qubit p) with Hamming weight >= threshold: the
    basis states the v1 oracle marks. Kept as-is so v1 circuits are reproduced gate for gate.
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
    Hamming-weight (cardinality) oracle on n_items + 1 qubits (qubit n_items is the ancilla,
    assumed already in |->):

        O|b>|-> = -|b>|->  if |b| >= threshold,   |b>|->  otherwise.

    One multi-controlled X per marked state, X gates flipping the zero-valued controls. This marks
    states by itemset SIZE only; it never looks at transactions. Special case of
    build_oracle_for_states.
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


def build_oracle_for_states(n_items: int, marked_indices: Sequence[int]) -> QuantumCircuit:
    """
    Oracle marking exactly the given basis-state indices (bit p of an index is qubit p), on
    n_items + 1 qubits with the ancilla assumed in |->. The marked set is supplied by the caller,
    i.e. precomputed classically; the circuit only applies the phase flip.

    Cost: one multi-controlled X per marked state, so oracle size grows linearly in M.
    """
    indices = [int(i) for i in marked_indices]
    if len(set(indices)) != len(indices):
        raise ValueError("marked_indices contains duplicates")
    if not indices:
        raise ValueError("marked_indices is empty; Grover search needs at least one marked state")
    if any(not (0 <= i < 2**n_items) for i in indices):
        raise ValueError(f"marked index out of range for {n_items} qubits")

    ancilla = n_items
    qc = QuantumCircuit(n_items + 1, name="oracle_states")
    for i in sorted(indices):
        zero_positions = [p for p in range(n_items) if not (i >> p) & 1]
        for p in zero_positions:
            qc.x(p)
        if n_items == 1:
            qc.cx(0, ancilla)
        else:
            qc.mcx(list(range(n_items)), ancilla)
        for p in zero_positions:
            qc.x(p)
    return qc


# --------------------------------------------------------------------------
# Diffusion
# --------------------------------------------------------------------------

def _phase_flip_all_ones(qc: QuantumCircuit, n_items: int) -> None:
    """Flip the sign of |1...1> (C^{n-1}Z)."""
    if n_items == 1:
        qc.z(0)
    else:
        qc.h(n_items - 1)
        qc.mcx(list(range(n_items - 1)), n_items - 1)
        qc.h(n_items - 1)


def build_diffusion(n_items: int, preparation: QuantumCircuit | None = None) -> QuantumCircuit:
    """
    Diffusion over the n_items item qubits (ancilla untouched).

    preparation=None: the Hadamard diffusion H^n X^n C^{n-1}Z X^n H^n, i.e. a reflection about the
    UNIFORM state (equal to 2|s><s| - I up to a global phase). Correct only for the uniform start.

    preparation=A: the matched diffusion A X^n C^{n-1}Z X^n A^dagger, a reflection about A|0>
    (up to a global phase). Correct for any start state; reduces to the Hadamard form when A = H^n.
    """
    qc = QuantumCircuit(n_items, name="diffusion")
    if preparation is None:
        qc.h(range(n_items))
        qc.x(range(n_items))
        _phase_flip_all_ones(qc, n_items)
        qc.x(range(n_items))
        qc.h(range(n_items))
        return qc

    if preparation.num_qubits != n_items:
        raise ValueError("preparation must act on exactly n_items qubits")
    qc.compose(preparation.inverse(), inplace=True)
    qc.x(range(n_items))
    _phase_flip_all_ones(qc, n_items)
    qc.x(range(n_items))
    qc.compose(preparation, inplace=True)
    return qc


# --------------------------------------------------------------------------
# Full circuit
# --------------------------------------------------------------------------

@dataclass
class CircuitInfo:
    """
    Metadata about a built circuit.

    theta is the rotation angle of the actual start state, asin(sqrt(P_0)); for the uniform start
    this is asin(sqrt(M/N)). theoretical_p is the closed-form noiseless success probability and is
    NaN when no closed form applies (ansatz start with the mismatched Hadamard diffusion).
    """
    n_items: int
    threshold: int
    r: int
    M: int
    N: int
    theta: float
    theoretical_p: float
    initial_state: str = "uniform"
    diffusion: str = "matched"
    start_marked_probability: float = nan
    marked_indices: tuple[int, ...] = field(default_factory=tuple)


def build_grover_circuit(
    n_items: int,
    threshold: int,
    r: int,
    reps: int = 1,
    measure: bool = True,
    initial_state: str = "ansatz",
    seed: int = 42,
    diffusion: str = "matched",
    marked_states: Sequence[int] | None = None,
) -> tuple[QuantumCircuit, CircuitInfo]:
    """
    Compose U = (D . O)^r . A on n_items + 1 qubits and measure the item qubits.

    marked_states: basis-state indices to mark (precomputed classically). If None, the v1
    cardinality oracle marks every state of Hamming weight >= threshold; if given, `threshold` is
    ignored.

    initial_state: "uniform" (H^n) or "ansatz" (bound EfficientSU2, parameters from `seed`).

    diffusion: "matched" (reflection about A|0>, correct for every start state) or "hadamard"
    (reflection about the uniform state; MISMATCHED for the ansatz start, kept to reproduce v1).

    The returned circuit has no free parameters and runs on any backend. info carries M, N and the
    closed-form noiseless probability where one exists.
    """
    if r < 0:
        raise ValueError("r must be non-negative")
    if diffusion not in DIFFUSIONS:
        raise ValueError(f"diffusion must be one of {DIFFUSIONS}")

    prep = build_start_preparation(n_items, reps=reps, kind=initial_state, seed=seed)
    qc = QuantumCircuit(n_items + 1, n_items)
    qc.compose(prep, qubits=range(n_items), inplace=True)
    prepare_ancilla_minus(qc, n_items)

    if marked_states is None:
        indices = cardinality_marked_indices(n_items, threshold)
        oracle = build_oracle(n_items, threshold)
    else:
        indices = sorted(int(i) for i in marked_states)
        oracle = build_oracle_for_states(n_items, indices)

    matched = diffusion == "matched" or initial_state == "uniform"
    d_circuit = build_diffusion(n_items, preparation=prep if diffusion == "matched" else None)

    for _ in range(r):
        qc.compose(oracle, qubits=range(n_items + 1), inplace=True)
        qc.compose(d_circuit, qubits=range(n_items), inplace=True)

    if measure:
        qc.measure(range(n_items), range(n_items))

    M = len(indices)
    N = 2**n_items
    p0 = start_marked_probability(prep, indices)
    info = CircuitInfo(
        n_items=n_items,
        threshold=threshold,
        r=r,
        M=M,
        N=N,
        theta=asin(sqrt(min(max(p0, 0.0), 1.0))),
        theoretical_p=success_probability_from_start(p0, r) if matched else nan,
        initial_state=initial_state,
        diffusion=diffusion,
        start_marked_probability=p0,
        marked_indices=tuple(indices),
    )
    return qc, info


def exact_success_probability(
    n_items: int,
    threshold: int,
    r: int,
    **kwargs,
) -> float:
    """
    Exact noiseless P(marked) of the circuit build_grover_circuit would build, from its
    statevector (no shot noise). Valid for any start state and either diffusion, including the
    mismatched case where no closed form exists. Practical up to about n_items = 10.
    """
    qc, info = build_grover_circuit(n_items, threshold, r, measure=False, **kwargs)
    probs = Statevector.from_instruction(qc).probabilities(qargs=list(range(n_items)))
    return float(sum(probs[i] for i in info.marked_indices))
