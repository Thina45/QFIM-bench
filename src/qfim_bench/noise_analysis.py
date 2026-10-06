"""
noise_analysis.py — Stage 6 analysis module: distribution-level comparison
between ideal, noisy-simulated, and (optionally) real-hardware execution of
the same circuit, via total variation distance (Eq. 7 in the companion
paper), with uncertainty estimated across repeated runs rather than
reported as a bare point value.

This module deliberately takes `Backend` instances (SimulatorBackend,
NoisySimulatorBackend, HardwareBackend — see backends.py) rather than
being specific to the QFIM oracle circuit, so it can compare ANY circuit
across ANY two backends. This generality is what distinguishes qfim-bench
from a QFIM-specific tool: the noise-characterization capability is a
reusable instrument, not a one-off script tied to a single experiment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .statistics import TVDReport, tvd_with_uncertainty

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

    from .backends import Backend


@dataclass
class DistributionComparison:
    backend_a_name: str
    backend_b_name: str
    tvd: TVDReport


def compare_distributions(
    circuit: "QuantumCircuit",
    backends: dict[str, "Backend"],
    shots: int,
    n_repeats: int = 1,
) -> list[DistributionComparison]:
    """
    Run `circuit` on every backend in `backends` (a name -> Backend dict,
    e.g. {"ideal": SimulatorBackend(), "noisy": NoisySimulatorBackend(),
    "hardware": HardwareBackend()}), n_repeats times each, and return the
    pairwise TVD between every pair of backends, each with an uncertainty
    estimate when n_repeats > 1 (via statistics.tvd_with_uncertainty).

    With n_repeats=1 (the default), each TVDReport.summary is None and
    only TVDReport.point_estimate is meaningful — matching the companion
    paper's own single-run TVD table (Section 6, TVD=0.097 vs 0.606),
    which can be reproduced exactly by calling this with n_repeats=1 and
    two backends named "ideal" and "noisy" (or "hardware").

    Every pairwise comparison is returned (not just adjacent pairs), so
    comparing 3 backends yields 3 DistributionComparison objects: (A,B),
    (A,C), (B,C).
    """
    if shots <= 0:
        raise ValueError("shots must be positive")
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    if len(backends) < 2:
        raise ValueError("backends must contain at least 2 entries to compare")

    # Run each backend n_repeats times, collecting counts dicts.
    counts_by_backend: dict[str, list[dict[str, int]]] = {}
    for name, backend in backends.items():
        runs = []
        for _ in range(n_repeats):
            result = backend.run(circuit, shots)
            runs.append(result.counts)
        counts_by_backend[name] = runs

    names = list(backends.keys())
    comparisons = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            tvd_report = tvd_with_uncertainty(
                counts_by_backend[a], counts_by_backend[b]
            )
            comparisons.append(
                DistributionComparison(backend_a_name=a, backend_b_name=b, tvd=tvd_report)
            )

    return comparisons


def compare_counts(
    counts_a: dict[str, int],
    counts_b: dict[str, int],
    label_a: str = "A",
    label_b: str = "B",
) -> DistributionComparison:
    """
    Lower-level entry point: compare two already-obtained counts dicts
    directly, without needing live Backend objects or a circuit — useful
    for re-analyzing previously collected hardware results (e.g. the
    counts from a completed IBM Quantum job) without re-running anything.
    """
    tvd_report = tvd_with_uncertainty([counts_a], [counts_b])
    return DistributionComparison(backend_a_name=label_a, backend_b_name=label_b, tvd=tvd_report)
