"""
reproducibility.py — Stage 6 analysis module: configurable repeated-run
reproducibility check for any circuit on any backend, reporting mean, SD,
coefficient of variation, and a confidence interval (via statistics.py)
rather than a single uncertainty-free number.

Generalizes the companion paper's n=2 paired reproducibility check
(Section 6: CV=0.82% at r=2) into an n-configurable utility — the paper's
own check is reproduced exactly by calling repeated_run_check(..., n_runs=2,
shots=8192, metric_fn=<empirical success probability>).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from .statistics import RunSummary, summarize_runs

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

    from .backends import Backend, ExecutionResult


@dataclass
class ReproducibilityReport:
    backend_name: str
    n_runs: int
    shots: int
    metric_values: list[float]
    summary: RunSummary


def repeated_run_check(
    circuit: "QuantumCircuit",
    backend: "Backend",
    n_runs: int,
    shots: int,
    metric_fn: Callable[["ExecutionResult"], float],
    confidence_level: float = 0.95,
) -> ReproducibilityReport:
    """
    Run `circuit` on `backend` n_runs times with otherwise entirely fixed
    conditions (same circuit object, same shots each run), apply
    `metric_fn` to each run's ExecutionResult to extract a single scalar
    (e.g. empirical success probability, or a specific itemset's
    estimated support), and summarize the resulting list of values via
    statistics.summarize_runs — returning mean, SD, CV%, and a confidence
    interval rather than a bare point estimate.

    metric_fn is caller-supplied so this module stays agnostic to what
    "the metric" means for a given experiment. For example, to reproduce
    the companion paper's own empirical-success-probability metric:

        def empirical_success_probability(result):
            marked = sum(
                c for bits, c in result.counts.items() if bits.count("1") >= 2
            )
            return marked / result.shots

        report = repeated_run_check(
            circuit, backend, n_runs=2, shots=8192,
            metric_fn=empirical_success_probability,
        )

    Note: this issues n_runs separate backend.run() calls. On real
    hardware, this costs n_runs times the QPU time/queue wait of a single
    run — be deliberate about n_runs when backend is a HardwareBackend.
    """
    if n_runs < 1:
        raise ValueError("n_runs must be >= 1")
    if shots <= 0:
        raise ValueError("shots must be positive")

    values = []
    for _ in range(n_runs):
        result = backend.run(circuit, shots=shots)
        values.append(metric_fn(result))

    summary = summarize_runs(values, confidence_level=confidence_level)
    return ReproducibilityReport(
        backend_name=backend.name,
        n_runs=n_runs,
        shots=shots,
        metric_values=values,
        summary=summary,
    )
