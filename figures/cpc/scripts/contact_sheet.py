"""Render figures/cpc/contact_sheet.png: every figure's PNG, at reduced size, in a grid, for a
single quality-check pass (overlapping text, clipped labels, legends over data, inconsistent
colours). Not one of the CPC figures itself.

    python figures/cpc/scripts/contact_sheet.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

FIG = Path(__file__).resolve().parents[1]
NAMES = ["fig_a", "fig_b", "fig_c", "fig_d", "fig_e", "fig_f", "fig_g", "fig_h", "fig_i",
         "fig_j", "fig_k", "fig_l", "fig_m", "fig_n", "fig_o", "fig_s1"]


def main() -> None:
    n = len(NAMES)
    ncols = 3
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 5, nrows * 3.2))
    axes = axes.flatten()
    for ax, name in zip(axes, NAMES):
        path = FIG / f"{name}.png"
        if path.exists():
            img = mpimg.imread(path)
            ax.imshow(img)
        ax.set_title(name, fontsize=9)
        ax.axis("off")
    for ax in axes[n:]:
        ax.axis("off")
    fig.tight_layout()
    out = FIG / "contact_sheet.png"
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
