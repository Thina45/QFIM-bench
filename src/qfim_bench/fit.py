"""
fit.py: effective-fidelity-per-step fit for amplitude-amplification data.

Model. At step count g (Grover iterations, or the two-qubit gate count of the circuit), the
measured marked-state probability is

    p(g) = f^g * p_ideal(g) + (1 - f^g) * p_noise

where f in (0, 1] is the effective fidelity per step and p_noise is the probability the circuit
settles to when all coherence is lost (a free parameter in [0, 1]; for a fully depolarised
register it is M/N). Both f and p_noise are fitted by binomial maximum likelihood from the
observed (successes, shots) pairs; confidence intervals come from a parametric bootstrap
(resample counts from the fitted curve, refit).

Generic: nothing here knows about itemsets. Identifiability caveat: where p_ideal(g) is close to
p_noise at every observed g, f is not determined by the data and the bootstrap interval will be
wide; that is the correct reading, not a defect.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


@dataclass
class DecayFit:
    f: float
    p_noise: float
    f_ci: tuple[float, float]
    p_noise_ci: tuple[float, float]
    neg_log_likelihood: float
    n_bootstrap: int

    @property
    def half_life_steps(self) -> float:
        """Steps after which the coherent part has fallen to one half (inf if f == 1)."""
        return float("inf") if self.f >= 1 else float(np.log(0.5) / np.log(self.f))


def decay_model(g: np.ndarray, p_ideal: np.ndarray, f: float, p_noise: float) -> np.ndarray:
    w = f ** np.asarray(g, float)
    return w * np.asarray(p_ideal, float) + (1 - w) * p_noise


def _nll(params, g, p_ideal, k, n):
    f, pn = params
    p = np.clip(decay_model(g, p_ideal, f, pn), 1e-9, 1 - 1e-9)
    return -float(np.sum(k * np.log(p) + (n - k) * np.log1p(-p)))


def _fit_once(g, p_ideal, k, n, starts=((0.9, 0.3), (0.99, 0.1), (0.7, 0.5), (0.5, 0.05))):
    best = None
    for s in starts:
        res = minimize(_nll, s, args=(g, p_ideal, k, n), method="L-BFGS-B", bounds=[(1e-6, 1.0), (0.0, 1.0)])
        if best is None or res.fun < best.fun:
            best = res
    return best


def fit_fidelity_decay(
    g,
    p_ideal,
    successes,
    shots,
    n_bootstrap: int = 300,
    confidence: float = 0.95,
    seed: int = 0,
) -> DecayFit:
    """
    Fit f and p_noise to counts. g, p_ideal, successes, shots are equal-length sequences, one entry
    per measurement (repeat measurements at the same g may appear as separate entries).
    """
    g = np.asarray(g, float)
    p_ideal = np.asarray(p_ideal, float)
    k = np.asarray(successes, float)
    n = np.asarray(shots, float)
    if not (len(g) == len(p_ideal) == len(k) == len(n)):
        raise ValueError("g, p_ideal, successes and shots must have equal length")
    if len(g) < 3:
        raise ValueError("need at least 3 measurements to fit two parameters")

    best = _fit_once(g, p_ideal, k, n)
    f_hat, pn_hat = float(best.x[0]), float(best.x[1])

    rng = np.random.default_rng(seed)
    p_fit = decay_model(g, p_ideal, f_hat, pn_hat)
    fs, pns = [], []
    for _ in range(n_bootstrap):
        kb = rng.binomial(n.astype(int), np.clip(p_fit, 0, 1))
        rb = _fit_once(g, p_ideal, kb.astype(float), n)
        fs.append(rb.x[0])
        pns.append(rb.x[1])
    a = (1 - confidence) / 2
    return DecayFit(
        f=f_hat,
        p_noise=pn_hat,
        f_ci=(float(np.quantile(fs, a)), float(np.quantile(fs, 1 - a))),
        p_noise_ci=(float(np.quantile(pns, a)), float(np.quantile(pns, 1 - a))),
        neg_log_likelihood=float(best.fun),
        n_bootstrap=n_bootstrap,
    )
