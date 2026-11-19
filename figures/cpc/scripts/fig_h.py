"""Fig. H: transpiled Grover circuit, n=3, r=1 (the ladder_n3_M1_r1 circuit), drawn with Qiskit's
mpl drawer. Transpiled against FakeMarrakesh (optimization_level=3, seed_transpiler=42, matching the
campaign's HardwareBackend settings). FakeMarrakesh's coupling map is not an approximation here: a
read-only query of the live ibm_marrakesh backend (performed once, Phase 0) confirmed its
coupling_map is identical (352 edges, same edge set) to FakeMarrakesh's -- the topology is a fixed
hardware property that does not change with calibration, so drawing against FakeMarrakesh gives the
exact layout, not a stand-in. Writes figures/cpc/fig_h.{pdf,png}.

    python figures/cpc/scripts/fig_h.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from qiskit import transpile
from qiskit.visualization import circuit_drawer
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

from qfim_bench.circuit import build_grover_circuit

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
plt.style.use(str(FIG / "cpc.mplstyle"))


def main():
    qc, info = build_grover_circuit(
        n_items=3, threshold=0, r=1, initial_state="uniform", diffusion="matched",
        marked_states=[3], oracle_style="mcz", seed=42,
    )
    backend = FakeMarrakesh()
    transpiled = transpile(qc, backend=backend, optimization_level=3, seed_transpiler=42)

    fig = circuit_drawer(transpiled, output="mpl", style={"fontsize": 7}, fold=40)
    fig.set_size_inches(90 / 25.4 * 2, 90 / 25.4)
    fig.savefig(FIG / "fig_h.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_h.png", bbox_inches="tight", dpi=300)
    print("wrote", FIG / "fig_h.pdf", "and .png")
    print(f"depth={transpiled.depth()}, two_qubit_gates="
          f"{sum(v for k, v in transpiled.count_ops().items() if k in ('cz', 'ecr', 'cx'))}")


if __name__ == "__main__":
    main()
