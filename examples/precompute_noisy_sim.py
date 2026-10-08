"""Precompute seeded FakeMarrakesh noisy-simulator values for the archived hardware runs.

Writes campaigns/uniform_marrakesh/noisy_sim_seeded.json, which examples/dashboard.py reads
so the page does not re-run the noisy simulator on every load.

    PYTHONPATH=src python examples/precompute_noisy_sim.py
"""

import json
from pathlib import Path

from qfim_bench.backends import NoisySimulatorBackend
from qfim_bench.circuit import build_grover_circuit

OUT = Path(__file__).resolve().parents[1] / "campaigns" / "uniform_marrakesh" / "noisy_sim_seeded.json"


def main() -> None:
    values = {}
    for r in [1, 2, 3, 4]:
        qc, _ = build_grover_circuit(5, 2, r, initial_state="uniform", seed=42)
        counts = NoisySimulatorBackend(seed=42, optimization_level=1).run(qc, shots=8192).counts
        values[str(r)] = sum(c for b, c in counts.items() if b.count("1") >= 2) / sum(counts.values())
        print(f"r={r}: {values[str(r)]:.4f}")
    OUT.write_text(json.dumps({"backend": "FakeMarrakesh", "seed": 42, "shots": 8192,
                               "initial_state": "uniform", "marked_probability": values}, indent=2),
                   encoding="utf-8")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
