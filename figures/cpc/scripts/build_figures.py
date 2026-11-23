"""Build every CPC-revision figure from saved result files, in order, then the contact sheet.
Equivalent to `make figures`.

    python figures/cpc/scripts/build_figures.py
"""
import runpy
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ORDER = ["fig_a", "fig_b", "fig_c", "fig_d", "fig_e", "fig_f", "fig_g", "fig_h", "fig_i",
         "fig_j", "fig_k", "fig_l", "fig_m", "fig_n", "fig_o", "fig_s1"]


def main() -> None:
    for name in ORDER:
        print(f"--- {name} ---")
        runpy.run_path(str(SCRIPTS_DIR / f"{name}.py"), run_name="__main__")
    runpy.run_path(str(SCRIPTS_DIR / "contact_sheet.py"), run_name="__main__")


if __name__ == "__main__":
    sys.exit(main())
