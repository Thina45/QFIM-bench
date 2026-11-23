"""Item 4 of the CPC v4 pass: compare the existing depolarizing fit (Model 1: 2 free parameters,
f and p_noise, fit by binomial MLE to the ladder r-series) against a SPAM-explicit model (Model 2:
1 free parameter, f, fit by binomial MLE to the SAME ladder r-series, with p_noise fixed at the
theoretical floor M/N and the ideal curve scaled by a SPAM factor R = (1 - e_spam)^n, where e_spam
is a PLUG-IN estimate -- not fit to the ladder data -- from that session's own readout_zeros/ones
controls: e0 = 1 - P(all-zeros correct)^(1/n), e1 = 1 - P(all-ones correct)^(1/n), e_spam = (e0+e1)/2).
k for AIC/BIC counts only parameters estimated from the ladder r-series being compared (Model 1:
k=2; Model 2: k=1, since e_spam comes from an independent dataset, the readout controls, not the
r-series likelihood). Per session (Oct-8, Run 1, Run 3, Run 4) and globally (all three sizes
pooled); per-size fits are informational only (not separately AIC/BIC-ranked, since they are not
nested in the per-session N_FIT_PARAMS bookkeeping of the original Phase 1B pass).

Read-only: uses only saved results/hardware/*/*.json counts files and
review/preregistration/ladder_predictions.json. No new hardware runs.

    python analysis/two_param_spam_fit.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase1_cpc_revision import ideal_probability, marked_bitstrings  # noqa: E402

from qfim_bench.fit import decay_model, fit_fidelity_decay  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "cpc_v4"
OUT.mkdir(parents=True, exist_ok=True)
R_RANGE = range(0, 5)

SESSIONS = {
    "Oct8": {"A": (ROOT / "results/hardware/ladder_v2", [f"day{d}.json" for d in range(1, 6)], 3, 1),
             "B": (ROOT / "results/hardware/ladder_v2b", [f"B_run{r}.json" for r in range(1, 6)], 4, 2),
             "C": (ROOT / "results/hardware/ladder_v2b", [f"C_run{r}.json" for r in range(1, 6)], 5, 4)},
    "Run1": {t: (ROOT / "results/hardware/cpc_run1", [f"{t}_run{r}.json" for r in range(1, 6)],
                 n, M) for t, n, M in [("A", 3, 1), ("B", 4, 2), ("C", 5, 4)]},
    "Run3": {t: (ROOT / "results/hardware/cpc_run3", [f"{t}_run{r}.json" for r in range(1, 4)],
                 n, M) for t, n, M in [("A", 3, 1), ("B", 4, 2), ("C", 5, 4)]},
    "Run4": {t: (ROOT / "results/hardware/cpc_run4", [f"{t}_run{r}.json" for r in range(1, 6)],
                 n, M) for t, n, M in [("A", 3, 1), ("B", 4, 2), ("C", 5, 4)]},
}


def load_runs(dir_, files):
    return [json.loads((dir_ / f).read_text(encoding="utf-8")) for f in files]


def pooled_ladder(dir_, files, n, M, r):
    cid = f"ladder_n{n}_M{M}_r{r}"
    runs = load_runs(dir_, files)
    marked = marked_bitstrings(cid, n)
    tot_k, tot_n, gates = 0, 0, []
    for d in runs:
        c = d["counts"][cid]
        info = next(i for i, lbl in zip(d["job"]["circuits_info"], d["job"]["labels"]) if lbl == cid)
        gates.append(info["two_qubit_gates"])
        tot_k += sum(x for key, x in c.items() if key in marked)
        tot_n += sum(c.values())
    return tot_k, tot_n, float(np.mean(gates))


def pooled_readout(dir_, files, n, kind):
    cid = f"readout_n{n}_{kind}"
    target = "0" * n if kind == "zeros" else "1" * n
    runs = load_runs(dir_, files)
    tot_k, tot_n = 0, 0
    for d in runs:
        c = d["counts"][cid]
        tot_k += c.get(target, 0)
        tot_n += sum(c.values())
    return tot_k, tot_n


def nll(f, pn, g, ideal, k, n):
    p = np.clip(decay_model(np.asarray(g, float), np.asarray(ideal, float), f, pn), 1e-9, 1 - 1e-9)
    k, n = np.asarray(k, float), np.asarray(n, float)
    return -float(np.sum(k * np.log(p) + (n - k) * np.log1p(-p)))


def fit_model2(g, ideal_spam, k, n, M_over_N):
    def obj(f):
        return nll(f, M_over_N, g, ideal_spam, k, n)
    res = minimize_scalar(obj, bounds=(1e-6, 1.0), method="bounded")
    return float(res.x), float(res.fun)


def aic_bic(nll_val, k_params, n_data):
    return 2 * k_params + 2 * nll_val, k_params * math.log(n_data) + 2 * nll_val


def chi_square(f, pn, g, ideal, k, n):
    g, ideal, k, n = map(np.asarray, (g, ideal, k, n))
    p_fit = decay_model(g, ideal, f, pn)
    var = p_fit * (1 - p_fit) / n
    return float(np.sum(np.where(var > 0, (k / n - p_fit) ** 2 / var, 0.0)))


def session_spam(spec, n):
    (dir_, files, _, _) = spec
    k0, n0 = pooled_readout(dir_, files, n, "zeros")
    k1, n1 = pooled_readout(dir_, files, n, "ones")
    p0, p1 = k0 / n0, k1 / n1
    e0 = 1 - p0 ** (1 / n)
    e1 = 1 - p1 ** (1 / n)
    return (e0 + e1) / 2, p0, p1


def main():
    report = {}
    for session, tiers in SESSIONS.items():
        report[session] = {"per_size": {}}
        all_g, all_ideal_m1, all_ideal_m2, all_k, all_n = [], [], [], [], []
        for tier, spec in tiers.items():
            dir_, files, n, M = spec
            N = 2**n
            e_spam, p0, p1 = session_spam(spec, n)
            R = (1 - e_spam) ** n
            g_list, ideal_list, k_list, n_list = [], [], [], []
            for r in R_RANGE:
                k, tot_n, gates = pooled_ladder(dir_, files, n, M, r)
                g_list.append(gates)
                ideal_list.append(ideal_probability(M, N, r))
                k_list.append(k)
                n_list.append(tot_n)

            m1 = fit_fidelity_decay(g_list, ideal_list, k_list, n_list, n_bootstrap=0 if False else 50, seed=1)
            m1_nll = nll(m1.f, m1.p_noise, g_list, ideal_list, k_list, n_list)
            m1_chi2 = chi_square(m1.f, m1.p_noise, g_list, ideal_list, k_list, n_list)
            m1_aic, m1_bic = aic_bic(m1_nll, 2, len(g_list))

            ideal_spam = [p * R for p in ideal_list]
            f2, m2_nll = fit_model2(g_list, ideal_spam, k_list, n_list, M / N)
            m2_chi2 = chi_square(f2, M / N, g_list, ideal_spam, k_list, n_list)
            m2_aic, m2_bic = aic_bic(m2_nll, 1, len(g_list))

            dof = len(g_list) - 2
            report[session]["per_size"][tier] = {
                "n": n, "M": M, "e_spam": e_spam, "R_spam": R, "p_all_zeros": p0, "p_all_ones": p1,
                "model1_f_pnoise": {"f": m1.f, "p_noise": m1.p_noise, "nll": m1_nll,
                                     "chi_square": m1_chi2, "reduced_chi_square": m1_chi2 / dof if dof > 0 else None,
                                     "aic": m1_aic, "bic": m1_bic},
                "model2_f_spam": {"f": f2, "nll": m2_nll, "chi_square": m2_chi2,
                                   "reduced_chi_square": m2_chi2 / (len(g_list) - 1) if len(g_list) > 1 else None,
                                   "aic": m2_aic, "bic": m2_bic},
            }
            all_g.extend(g_list); all_ideal_m1.extend(ideal_list); all_ideal_m2.extend(ideal_spam)
            all_k.extend(k_list); all_n.extend(n_list)

        gm1 = fit_fidelity_decay(all_g, all_ideal_m1, all_k, all_n, n_bootstrap=50, seed=1)
        gm1_nll = nll(gm1.f, gm1.p_noise, all_g, all_ideal_m1, all_k, all_n)
        gm1_chi2 = chi_square(gm1.f, gm1.p_noise, all_g, all_ideal_m1, all_k, all_n)
        gm1_aic, gm1_bic = aic_bic(gm1_nll, 2, len(all_g))

        # global model 2 needs a single M/N -- not well-defined across mixed sizes, so report
        # global model 2 using the SAME per-point ideal_spam (already size-specific) and the
        # per-point M/N floor (also size-specific), consistent with how model1's p_noise is a
        # single global value fit across sizes -- model2's p_noise is instead the KNOWN per-point
        # floor, which varies by tier; this is noted explicitly, not glossed over.
        all_mn = []
        for tier, spec in tiers.items():
            _, _, n, M = spec
            all_mn.extend([M / 2**n] * len(R_RANGE))

        def gnll(f):
            tot = 0.0
            for g, ideal, k, n, mn in zip(all_g, all_ideal_m2, all_k, all_n, all_mn):
                p = float(np.clip(decay_model(np.array([g]), np.array([ideal]), f, mn)[0], 1e-9, 1 - 1e-9))
                tot += -(k * math.log(p) + (n - k) * math.log1p(-p))
            return tot

        res = minimize_scalar(gnll, bounds=(1e-6, 1.0), method="bounded")
        gf2, gm2_nll = float(res.x), float(res.fun)
        gm2_chi2 = sum(
            ((k / n - decay_model(np.array([g]), np.array([ideal]), gf2, mn)[0]) ** 2
             / (decay_model(np.array([g]), np.array([ideal]), gf2, mn)[0]
                * (1 - decay_model(np.array([g]), np.array([ideal]), gf2, mn)[0]) / n))
            for g, ideal, k, n, mn in zip(all_g, all_ideal_m2, all_k, all_n, all_mn)
        )
        gm2_aic, gm2_bic = aic_bic(gm2_nll, 1, len(all_g))

        report[session]["global"] = {
            "model1_f_pnoise": {"f": gm1.f, "p_noise": gm1.p_noise, "nll": gm1_nll,
                                 "chi_square": gm1_chi2, "reduced_chi_square": gm1_chi2 / (len(all_g) - 2),
                                 "aic": gm1_aic, "bic": gm1_bic},
            "model2_f_spam": {"f": gf2, "nll": gm2_nll, "chi_square": float(gm2_chi2),
                               "reduced_chi_square": float(gm2_chi2) / (len(all_g) - 1),
                               "aic": gm2_aic, "bic": gm2_bic},
        }
        print(f"=== {session} ===")
        print("global model1 (f,p_noise):", report[session]["global"]["model1_f_pnoise"])
        print("global model2 (f,spam):   ", report[session]["global"]["model2_f_spam"])

    (OUT / "two_param_spam_fit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'two_param_spam_fit.json'}")


if __name__ == "__main__":
    main()
