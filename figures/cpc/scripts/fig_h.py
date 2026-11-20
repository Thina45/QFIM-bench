"""Fig. H: the LOGICAL Grover circuit for n=3, M=1, r=1 (state preparation, oracle, diffusion as
labelled boxes, with barriers between stages, and measurement) -- illustrative of the circuit
structure, not a measured or transpiled result (replaces the earlier transpiled-circuit drawing).
Reuses qfim_bench.circuit's own building blocks (build_start_preparation, build_oracle_variant,
build_diffusion) so the diagram matches exactly what the ladder campaigns actually run (uniform
start, "mcz" oracle style, matched diffusion). Writes figures/cpc/fig_h.{pdf,png}.

    python figures/cpc/scripts/fig_h.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.visualization import circuit_drawer

from qfim_bench.circuit import build_diffusion, build_oracle_variant, build_start_preparation

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402

N_ITEMS = 3
MARKED = [3]  # M=1, matching ladder_n3_M1


def main():
    prep = build_start_preparation(N_ITEMS, kind="uniform")
    oracle = build_oracle_variant(N_ITEMS, MARKED, style="mcz")
    diffusion = build_diffusion(N_ITEMS, preparation=prep)

    qc = QuantumCircuit(N_ITEMS, N_ITEMS)
    # a leading/trailing space keeps each label clear of qiskit's own per-wire index text
    # (box width is sized to the label; without padding the "Diffusion" box -- the shortest
    # instruction -- was narrow enough that its index "1" touched the label text).
    qc.append(prep.to_gate(label=" State preparation $A$ "), range(N_ITEMS))
    qc.barrier()
    qc.append(oracle.to_gate(label=" Oracle (mcz) "), range(N_ITEMS))
    qc.barrier()
    qc.append(diffusion.to_gate(label=" Diffusion "), range(N_ITEMS))
    qc.barrier()
    qc.measure(range(N_ITEMS), range(N_ITEMS))

    fig = circuit_drawer(qc, output="mpl", style={"fontsize": 9}, fold=-1)
    fig.set_size_inches(190 / 25.4, 45 / 25.4)
    save_all(fig, "fig_h")


if __name__ == "__main__":
    main()
