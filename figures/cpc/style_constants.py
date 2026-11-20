"""Shared colour/style constants, so meaning maps to colour consistently across EVERY figure in
this set: n=3/4/5 always the same three colours; ideal/noise-model/hardware-twin always the same
linestyles; ibm_marrakesh/ibm_kingston always the same two colours. Okabe-Ito colour-blind-safe
palette (same hex values as cpc.mplstyle's axes.prop_cycle).
"""

# problem size n -> colour (tier A=n3, B=n4, C=n5 share these)
SIZE_COLOR = {3: "#0072B2", 4: "#D55E00", 5: "#009E73"}
TIER_TO_N = {"A": 3, "B": 4, "C": 5}
TIER_COLOR = {t: SIZE_COLOR[n] for t, n in TIER_TO_N.items()}

# reference curve -> linestyle (ideal vs simulated vs measured)
REF_LINESTYLE = {"ideal": "-", "noise_model": "--", "digital_twin": ":"}
REF_LABEL = {"ideal": "ideal", "noise_model": "FakeMarrakesh", "digital_twin": "digital twin (Phase 1E)"}

# device -> colour (independent of the n=3/4/5 palette, since Fig M compares devices not sizes)
DEVICE_COLOR = {"ibm_marrakesh": "#0072B2", "ibm_kingston": "#D55E00"}

# single/1.5/double column widths (mm), CPC (Elsevier) house style
WIDTH_SINGLE_MM = 90
WIDTH_ONEHALF_MM = 140
WIDTH_DOUBLE_MM = 190
MM = 1 / 25.4


def mm2in(w_mm: float, h_mm: float) -> tuple[float, float]:
    return w_mm * MM, h_mm * MM


def panel_label(ax, text: str, dx: float = -0.12, dy: float = 1.02) -> None:
    """Bold panel letter, e.g. '(a)', at the top-left of ax, OUTSIDE the axes (not a title)."""
    ax.text(dx, dy, text, transform=ax.transAxes, fontsize=9, fontweight="bold",
            ha="left", va="bottom")
