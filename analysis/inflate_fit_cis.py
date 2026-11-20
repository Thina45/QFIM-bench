"""Add goodness-of-fit-inflated confidence intervals to every depolarizing fit (Phase 1B Oct-8,
Run 1, Run 4). The binomial-bootstrap CI assumes the model fits within shot noise; reduced
chi-square is 15-250 for these fits (far above 1), so the raw CI is too narrow. Standard fix:
scale each CI's half-width (on each side of f) by sqrt(reduced_chi_square).

Adds a "f_ci95_inflated" field (and, for cpc_run1/cpc_run4 which lacked them, "chi_square",
"degrees_of_freedom", "reduced_chi_square") next to the existing "f_ci95"/"f_ci" field, in place,
for every per_size entry and the global fit, in:
    results/cpc_revision/phase1b_global_fit.json   (Oct-8)
    results/cpc_revision/cpc_run1_fit.json         (Run 1)
    results/cpc_revision/cpc_run4_fit.json         (Run 4)

Run 1/Run 4 chi-square is computed from their existing *_fit_residuals.csv (chi2_contrib column).

    python analysis/inflate_fit_cis.py
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPC = ROOT / "results" / "cpc_revision"


def inflate(ci: list[float], f: float, reduced_chi2: float) -> list[float]:
    scale = math.sqrt(reduced_chi2) if reduced_chi2 and reduced_chi2 > 0 else 1.0
    return [f - (f - ci[0]) * scale, f + (ci[1] - f) * scale]


def phase1b_oct8() -> None:
    path = CPC / "phase1b_global_fit.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    for tier, entry in d["per_size"].items():
        entry["f_ci95_inflated"] = inflate(entry["f_ci95"], entry["f"], entry["reduced_chi_square"])
    g = d["global"]
    g["f_ci95_inflated"] = inflate(g["f_ci95"], g["f"], g["reduced_chi_square"])
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"{path.name}: inflated CIs added")


def per_run(campaign: str, ci_key: str) -> None:
    fit_path = CPC / f"{campaign}_fit.json"
    res_path = CPC / f"{campaign}_fit_residuals.csv"
    d = json.loads(fit_path.read_text(encoding="utf-8"))

    chi2_by_tier: dict[str, float] = {}
    n_by_tier: dict[str, int] = {}
    with res_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            t = row["tier"]
            chi2_by_tier[t] = chi2_by_tier.get(t, 0.0) + float(row["chi2_contrib"])
            n_by_tier[t] = n_by_tier.get(t, 0) + 1

    for tier, entry in d["per_size"].items():
        chi2, n_pts = chi2_by_tier[tier], n_by_tier[tier]
        dof = n_pts - 2
        reduced = chi2 / dof if dof > 0 else float("nan")
        entry["chi_square"], entry["degrees_of_freedom"], entry["reduced_chi_square"] = chi2, dof, reduced
        entry[f"{ci_key}_inflated"] = inflate(entry[ci_key], entry["f"], reduced)

    g = d["global"]
    chi2_all = sum(chi2_by_tier.values())
    n_all = sum(n_by_tier.values())
    dof_all = n_all - 2
    reduced_all = chi2_all / dof_all if dof_all > 0 else float("nan")
    g["chi_square"], g["degrees_of_freedom"], g["reduced_chi_square"] = chi2_all, dof_all, reduced_all
    g[f"{ci_key}_inflated"] = inflate(g[ci_key], g["f"], reduced_all)

    fit_path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"{fit_path.name}: chi-square + inflated CIs added")


if __name__ == "__main__":
    phase1b_oct8()
    per_run("cpc_run1", "f_ci")
    per_run("cpc_run4", "f_ci")
