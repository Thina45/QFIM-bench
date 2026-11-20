"""Fig. L: local subgraph of the ibm_marrakesh coupling map (heavy-hex, from FakeMarrakesh's saved
coupling map -- read-only, no job submission; confirmed identical, 352 edges/same edge set, to the
live backend in a one-off Phase 0 check, see Fig. H/REPORT.md) containing every physical qubit
used at n=3,4,5 on 2026-10-08 (campaigns/ladder_v2, ladder_v2b) and Run 1, 2026-11-19
(campaigns/cpc_run1), plus every qubit within 2 coupling-graph hops of that set. Node positions
come from the FULL 156-qubit graph laid out once with Graphviz "neato" (conda-forge graphviz +
pygraphviz, planar/readable heavy-hex layout), then cropped to the local subgraph -- so relative
positions match the real device layout exactly, not a schematic. Every drawn qubit is labelled
with its index. Marker SHAPE (not just colour) encodes problem size (circle n=3, square n=4,
triangle n=5), so a qubit used by two sizes shows both overlaid markers.

    python figures/cpc/scripts/fig_l.py
"""
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import SIZE_COLOR, mm2in, panel_label  # noqa: E402

# conda-forge graphviz's binaries (neato) aren't on PATH by default in this environment
_GV_BIN = Path(sys.executable).parent / "Library" / "bin"
if _GV_BIN.exists():
    os.environ["PATH"] = str(_GV_BIN) + os.pathsep + os.environ.get("PATH", "")

import pygraphviz as pgv  # noqa: E402

# busy (two-qubit-gate-bearing) physical qubits, from the saved campaign manifests (circuits_info)
OCT8 = {3: [5, 6, 7], 4: [98, 110, 111, 112], 5: [91, 98, 110, 111, 112]}
RUN1 = {3: [53, 54, 55], 4: [137, 146, 147, 148], 5: [1, 2, 3, 4, 16]}
MARKER = {3: "o", 4: "s", 5: "^"}


def full_layout(backend):
    edges = {tuple(sorted(e)) for e in backend.coupling_map.get_edges()}
    g = pgv.AGraph(strict=True, overlap="false")
    for q in range(backend.num_qubits):
        g.add_node(q)
    for a, b in edges:
        g.add_edge(a, b)
    g.layout(prog="neato")
    pos = {int(n): tuple(map(float, n.attr["pos"].split(","))) for n in g.nodes()}
    return pos, edges


def khop_closure(seed_qubits, edges, k):
    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    frontier = set(seed_qubits)
    seen = set(seed_qubits)
    for _ in range(k):
        nxt = set()
        for q in frontier:
            nxt |= adj.get(q, set())
        nxt -= seen
        seen |= nxt
        frontier = nxt
    return seen


def panel(ax, pos, edges, local_qubits, used_by_n):
    for a, b in edges:
        if a in local_qubits and b in local_qubits:
            ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#BBBBBB",
                    linewidth=0.7, zorder=1)
    for q in local_qubits:
        ax.scatter([pos[q][0]], [pos[q][1]], s=90, color="#EEEEEE", edgecolor="0.6",
                   linewidth=0.5, zorder=2)
        ax.annotate(str(q), pos[q], fontsize=5, ha="center", va="center", zorder=5)
    for n, qubits in used_by_n.items():
        for q in qubits:
            ax.scatter([pos[q][0]], [pos[q][1]], s=170, marker=MARKER[n], facecolor="none",
                       edgecolor=SIZE_COLOR[n], linewidth=1.6, zorder=4)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    for spine in ax.spines.values():
        spine.set_visible(False)


def main():
    backend = FakeMarrakesh()
    pos, edges = full_layout(backend)

    all_used = sorted({q for qs in OCT8.values() for q in qs} | {q for qs in RUN1.values() for q in qs})
    local = khop_closure(all_used, edges, k=2)

    fig, axes = plt.subplots(1, 2, figsize=mm2in(140, 85))

    panel(axes[0], pos, edges, local, OCT8)
    panel_label(axes[0], "(a)")
    axes[0].text(0.5, -0.03, "2026-10-08", transform=axes[0].transAxes, ha="center", fontsize=7.5)

    panel(axes[1], pos, edges, local, RUN1)
    panel_label(axes[1], "(b)")
    axes[1].text(0.5, -0.03, "Run 1, 2026-11-19", transform=axes[1].transAxes, ha="center", fontsize=7.5)

    import matplotlib.lines as mlines
    handles = [mlines.Line2D([], [], marker=MARKER[n], linestyle="none", markerfacecolor="none",
                              markeredgecolor=SIZE_COLOR[n], markeredgewidth=1.6, markersize=8,
                              label=f"n={n}") for n in (3, 4, 5)]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, fontsize=7.5, frameon=False)

    save_all(fig, "fig_l")


if __name__ == "__main__":
    main()
