"""examples/generic_bell_demo.py: domain-agnostic demo of the generic layer.

This script imports only the simulator backend and the statistics helpers. It does not
import any QFIM-specific module (circuit, encoding, postprocessing, classical). It shows
that the generic layer runs on an arbitrary circuit with no Grover or itemset logic.

    python examples/generic_bell_demo.py
"""

from qiskit import QuantumCircuit

from qfim_bench.backends import SimulatorBackend
from qfim_bench.statistics import counts_to_probabilities, total_variation_distance


def bell_circuit() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def main() -> None:
    shots = 8192
    ideal_a = SimulatorBackend(seed=1).run(bell_circuit(), shots=shots).counts
    ideal_b = SimulatorBackend(seed=2).run(bell_circuit(), shots=shots).counts

    p_a = counts_to_probabilities(ideal_a)
    p_b = counts_to_probabilities(ideal_b)
    print("two seeded runs of the same ideal Bell circuit:")
    for k in sorted(set(p_a) | set(p_b)):
        print(f"  |{k}>  run1 {p_a.get(k, 0):.4f}  run2 {p_b.get(k, 0):.4f}")
    print(f"TVD between the two runs: {total_variation_distance(p_a, p_b):.4f}")
    print("expected: about 0.5 mass on |00> and |11>, near-zero on |01> and |10>; TVD near 0.")


if __name__ == "__main__":
    main()
