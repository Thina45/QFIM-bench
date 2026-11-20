"""Fig. J: software architecture, redrawn as a clean vector diagram (boxes + arrows) using the
real module names from src/qfim_bench/. Layer B is the 5-stage application pipeline pipeline.py
wires together (its own docstring: preprocessing -> encoding -> circuit -> backends ->
postprocessing); Layer A is the opt-in characterization layer (noise_analysis, reproducibility,
scaling, classical, search_cost, statistics, intervals, tvd_calibration, fit, manifest,
noise_scaling) that calls into pipeline.py's results rather than being bundled into every run.
backends.py exposes one interface (Backend.run) to three concrete backends: SimulatorBackend
(ideal), NoisySimulatorBackend (FakeMarrakesh/noise model), HardwareBackend (IBM Quantum).
No data; illustrates code structure only. Writes figures/cpc/fig_j.{pdf,eps,tiff,png}.

    python figures/cpc/scripts/fig_j.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in  # noqa: E402

LAYER_B = ["preprocessing.py", "encoding.py", "circuit.py", "postprocessing.py", "classical.py", "manifest.py"]
LAYER_A = ["search_cost.py", "statistics.py", "intervals.py", "tvd_calibration.py", "fit.py",
           "noise_analysis.py", "reproducibility.py", "scaling.py", "noise_scaling.py"]
BACKENDS = ["SimulatorBackend\n(ideal)", "NoisySimulatorBackend\n(noise model)", "HardwareBackend\n(IBM Quantum)"]


def box(ax, xy, w, h, text, fc="white", ec="0.2", fontsize=7.5, fontweight="normal"):
    x, y = xy
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                            linewidth=0.9, edgecolor=ec, facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            fontweight=fontweight)
    return (x, y, w, h)


def arrow(ax, p0, p1, color="0.3"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=9,
                                  linewidth=0.9, color=color, shrinkA=1, shrinkB=1))


def main():
    fig, ax = plt.subplots(figsize=mm2in(190, 110))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # Layer B: pipeline.py orchestrating the 5-stage pipeline
    pipe = box(ax, (36, 50), 28, 6, "pipeline.py\n(run_qfim_bench)", fc="#E8EEF7", fontweight="bold")
    n = len(LAYER_B)
    bw, gap = 14.5, 1.0
    total_w = n * bw + (n - 1) * gap
    x0 = 50 - total_w / 2
    stage_boxes = []
    for i, mod in enumerate(LAYER_B):
        bx = x0 + i * (bw + gap)
        stage_boxes.append(box(ax, (bx, 38), bw, 7, mod, fc="#F2F2F2", fontsize=6.8))
    for i in range(n - 1):
        x1 = stage_boxes[i][0] + stage_boxes[i][2]
        x2 = stage_boxes[i + 1][0]
        arrow(ax, (x1, 38 + 3.5), (x2, 38 + 3.5))
    arrow(ax, (50, 50), (50, 45))
    ax.text(50, 46.3, "Layer B -- application pipeline", ha="center", fontsize=7.5, style="italic")

    # three backends, called from the circuit.py/backends.py stage
    bx0 = 50 - (3 * 22 + 2 * 3) / 2
    backend_boxes = []
    for i, label in enumerate(BACKENDS):
        bbx = bx0 + i * 25
        backend_boxes.append(box(ax, (bbx, 24), 22, 8, label, fc="#FBEEE6", fontsize=7))
    circuit_box = stage_boxes[2]
    for bb in backend_boxes:
        arrow(ax, (circuit_box[0] + circuit_box[2] / 2, 38), (bb[0] + bb[2] / 2, 32))
    ax.text(50, 21.5, "one shared interface: Backend.run(circuit, shots)", ha="center",
            fontsize=7, style="italic")

    # Layer A: characterization modules, called on pipeline.py's results (opt-in)
    m = len(LAYER_A)
    aw, agap = 9.6, 0.8
    total_aw = m * aw + (m - 1) * agap
    ax0 = 50 - total_aw / 2
    a_boxes = []
    for i, mod in enumerate(LAYER_A):
        abx = ax0 + i * (aw + agap)
        a_boxes.append(box(ax, (abx, 4), aw, 7, mod, fc="#EAF3EA", fontsize=6.2))
    for ab in a_boxes:
        arrow(ax, (ab[0] + ab[2] / 2, 11), (ab[0] + ab[2] / 2, 15))
    ax.text(50, 16.3, "Layer A -- characterization (opt-in, reads pipeline.py's results)",
            ha="center", fontsize=7.5, style="italic")

    save_all(fig, "fig_j")


if __name__ == "__main__":
    main()
