"""Fig. L: ibm_marrakesh coupling graph (heavy-hex, from FakeMarrakesh's saved coupling map --
read-only, no job submission; its coupling_map was confirmed identical, 352 edges/same edge set,
to the live backend in a one-off Phase 0 check, see Fig. H/REPORT.md), highlighting the physical
qubits used by the gate-bearing (two-qubit-gate) circuits at n=3,4,5 on 2026-10-08
(campaigns/ladder_v2, ladder_v2b) vs Run 1, 2026-11-19 (campaigns/cpc_run1) -- two panels, one per
date, qubit indices labelled only for the used qubits. Colour encodes problem size n (same
palette as every other figure in this set). Node positions are a force-directed layout of the
152-qubit heavy-hex coupling graph (rustworkx spring_layout, fixed seed) -- a schematic of
connectivity, not the literal chip floorplan (Graphviz, which qiskit's own chip-floorplan
plot_gate_map needs, is not installed in this environment).

    python figures/cpc/scripts/fig_l.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import rustworkx as rx
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import SIZE_COLOR, mm2in, panel_label  # noqa: E402

# busy (two-qubit-gate-bearing) physical qubits, from the saved campaign manifests (circuits_info)
OCT8 = {3: [5, 6, 7], 4: [98, 110, 111, 112], 5: [91, 98, 110, 111, 112]}
RUN1 = {3: [53, 54, 55], 4: [137, 146, 147, 148], 5: [1, 2, 3, 4, 16]}


def build_graph(backend):
    g = rx.PyGraph()
    g.add_nodes_from(range(backend.num_qubits))
    edges = {tuple(sorted(e)) for e in backend.coupling_map.get_edges()}
    g.add_edges_from([(a, b, None) for a, b in edges])
    return g


def panel(ax, pos, g, used_by_n):
    xs = [pos[q][0] for q in g.node_indices()]
    ys = [pos[q][1] for q in g.node_indices()]
    for a, b in g.edge_list():
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#CCCCCC",
                linewidth=0.5, zorder=1)
    ax.scatter(xs, ys, s=5, color="#DDDDDD", zorder=2, linewidths=0)
    for n, qubits in used_by_n.items():
        qx = [pos[q][0] for q in qubits]
        qy = [pos[q][1] for q in qubits]
        ax.scatter(qx, qy, s=30, color=SIZE_COLOR[n], zorder=3, edgecolor="0.2", linewidth=0.5)
        for q in qubits:
            ax.annotate(str(q), pos[q], fontsize=5.5, ha="center", va="bottom",
                        xytext=(0, 3), textcoords="offset points", zorder=4)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def main():
    backend = FakeMarrakesh()
    g = build_graph(backend)
    pos = rx.spring_layout(g, seed=7, num_iter=200)

    fig, axes = plt.subplots(1, 2, figsize=mm2in(140, 75))

    panel(axes[0], pos, g, OCT8)
    panel_label(axes[0], "(a)")
    axes[0].text(0.5, -0.03, "2026-10-08", transform=axes[0].transAxes, ha="center", fontsize=7.5)

    panel(axes[1], pos, g, RUN1)
    panel_label(axes[1], "(b)")
    axes[1].text(0.5, -0.03, "Run 1, 2026-11-19", transform=axes[1].transAxes, ha="center", fontsize=7.5)

    import matplotlib.lines as mlines
    handles = [mlines.Line2D([], [], marker="o", linestyle="none", color=SIZE_COLOR[n],
                              markersize=6, label=f"n={n}") for n in (3, 4, 5)]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, fontsize=7.5, frameon=False)

    save_all(fig, "fig_l")


if __name__ == "__main__":
    main()
