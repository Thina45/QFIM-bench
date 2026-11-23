"""Fig. O (new, item 6 of the CPC v4 pass): Layer A generality -- two non-Grover examples.
(a) GHZ ladder (examples/ghz_ladder.py): success probability (P(all-zeros or all-ones)) vs
two-qubit gate count (n-1 CNOTs), n=3..6, ideal=1.0 at every point by construction, with the
fitted depolarizing curve. (b) TFIM Trotter (examples/tfim_trotter.py): return probability
P(all-zeros) vs two-qubit gate count, n=4..6 x 1-4 Trotter steps, ideal = noiseless statevector of
the same trotterized circuit, coloured by n. Both simulated only (ibm_marrakesh calibration
snapshot noise model via NoisySimulatorBackend); no hardware job submitted.

    python figures/cpc/scripts/fig_o.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
FIG = ROOT / "figures" / "cpc"
sys.path.insert(0, str(FIG))
plt.style.use(str(FIG / "cpc.mplstyle"))
from save_utils import save_all  # noqa: E402
from style_constants import mm2in, panel_label  # noqa: E402

V4 = ROOT / "results" / "cpc_v4"


def decay_model(g, f, p_noise, p_ideal):
    w = f ** np.asarray(g, float)
    return w * np.asarray(p_ideal, float) + (1 - w) * p_noise


def main():
    ghz = json.loads((V4 / "ghz_ladder.json").read_text())
    tfim = json.loads((V4 / "tfim_trotter.json").read_text())

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=mm2in(190, 65))

    gs = [r["two_qubit_gates"] for r in ghz["rows"]]
    ys = [r["noisy_success_probability"] for r in ghz["rows"]]
    ax.scatter(gs, ys, color="#0072B2", zorder=3, label="noisy simulation")
    g_line = np.linspace(min(gs), max(gs), 100)
    ax.plot(g_line, decay_model(g_line, ghz["fit"]["f"], ghz["fit"]["p_noise"], 1.0),
            color="#0072B2", alpha=0.7, linewidth=0.9, label=f"fit f={ghz['fit']['f']:.4f}")
    ax.set_xlabel("two-qubit gate count (CNOT chain)")
    ax.set_ylabel("P(all-zeros or all-ones)")
    ax.set_xticks(gs)
    ax.legend(fontsize=7, loc="lower left")
    panel_label(ax, "(a)")

    colors = {4: "#0072B2", 5: "#D55E00", 6: "#009E73"}
    for n in (4, 5, 6):
        rows = [r for r in tfim["rows"] if r["n"] == n]
        gs2 = [r["two_qubit_gates"] for r in rows]
        ys2 = [r["noisy_return_probability"] for r in rows]
        ideal2 = [r["ideal_return_probability"] for r in rows]
        ax2.scatter(gs2, ys2, color=colors[n], zorder=3, label=f"n={n}")
        ax2.plot(gs2, ideal2, "--", color=colors[n], alpha=0.5, linewidth=0.8)
    ax2.set_xlabel("two-qubit gate count (RZZ chain x steps)")
    ax2.set_ylabel("P(all-zeros), noisy (solid) vs ideal (dashed)")
    ax2.legend(fontsize=7, loc="upper right")
    panel_label(ax2, "(b)")

    save_all(fig, "fig_o")


if __name__ == "__main__":
    main()
