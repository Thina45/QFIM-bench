"""save_all(fig, stem): write a figure in every format the CPC submission needs --
vector PDF (fonts embedded via pdf.fonttype=42 in cpc.mplstyle), EPS, TIFF at 1000 dpi
(LZW-compressed), and PNG at 600 dpi for on-screen preview. One call per figure script.
"""
from pathlib import Path

FIG_DIR = Path(__file__).resolve().parent


def save_all(fig, stem: str) -> dict:
    paths = {}
    pdf_path = FIG_DIR / f"{stem}.pdf"
    fig.savefig(pdf_path)
    paths["pdf"] = pdf_path

    eps_path = FIG_DIR / f"{stem}.eps"
    fig.savefig(eps_path)
    paths["eps"] = eps_path

    tiff_path = FIG_DIR / f"{stem}.tiff"
    fig.savefig(tiff_path, dpi=1000, pil_kwargs={"compression": "tiff_lzw"})
    paths["tiff"] = tiff_path

    png_path = FIG_DIR / f"{stem}.png"
    fig.savefig(png_path, dpi=600)
    paths["png"] = png_path

    print(f"wrote {stem}: " + ", ".join(f"{k}={v.stat().st_size} B" for k, v in paths.items()))
    return paths
