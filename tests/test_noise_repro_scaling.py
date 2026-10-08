"""Noisy simulation (FakeMarrakesh), noise comparison, reproducibility and complexity scaling."""

import pytest

from qfim_bench.backends import NoisySimulatorBackend, SimulatorBackend
from qfim_bench.circuit import build_grover_circuit
from qfim_bench.noise_analysis import compare_counts, compare_distributions
from qfim_bench.reproducibility import repeated_run_check
from qfim_bench.scaling import growth_factors, sweep_item_counts


@pytest.fixture(scope="module")
def r1_circuit():
    # v1 hardware used the mismatched Hadamard diffusion, so reproduce that circuit explicitly
    qc, _ = build_grover_circuit(5, 2, 1, initial_state="ansatz", seed=42, diffusion="hadamard")
    return qc


def test_noisy_backend_runs_fake_marrakesh(r1_circuit):
    res = NoisySimulatorBackend(fake_backend_name="FakeMarrakesh", seed=42).run(r1_circuit, shots=2048)
    assert sum(res.counts.values()) == 2048


def test_noisy_closer_to_hardware_reference_than_ideal(r1_circuit):
    """Reproduces the paper's qualitative TVD ordering: the noisy model is closer to
    the hardware reference than the ideal model. The hardware reference counts are
    the r=1 ibm_marrakesh job; they are supplied from the paper's data, not re-run."""
    import json
    from pathlib import Path

    ref = Path(__file__).resolve().parents[2].parent / "Conference" / "resubmission" / "results" / "raw" / "grover_r1.json"
    if not ref.exists():
        pytest.skip("paper hardware reference not available in this checkout")
    hw = json.loads(ref.read_text(encoding="utf-8"))["full_counts"]

    ideal = SimulatorBackend(seed=42).run(r1_circuit, shots=8192).counts
    noisy = NoisySimulatorBackend(fake_backend_name="FakeMarrakesh", seed=42).run(r1_circuit, shots=8192).counts
    tvd_ideal_hw = compare_counts(ideal, hw, "ideal", "hardware").tvd.point_estimate
    tvd_noisy_hw = compare_counts(noisy, hw, "noisy", "hardware").tvd.point_estimate
    assert tvd_noisy_hw < tvd_ideal_hw


def test_compare_counts_identical_is_zero():
    c = {"00": 50, "11": 50}
    assert compare_counts(c, c, "a", "b").tvd.point_estimate == pytest.approx(0.0)


def test_compare_distributions_ideal_vs_ideal_is_zero(r1_circuit):
    backends = {"ideal_a": SimulatorBackend(seed=1), "ideal_b": SimulatorBackend(seed=2)}
    out = compare_distributions(r1_circuit, backends, shots=8192)
    assert len(out) == 1
    # Two independent 8192-shot samples of the same 32-outcome distribution have an
    # expected TVD of about 0.035 from sampling noise alone; 0.06 is roughly 2x that.
    assert out[0].tvd.point_estimate < 0.06


def test_repeated_run_check_returns_sensible_cv(r1_circuit):
    rep = repeated_run_check(
        r1_circuit,
        SimulatorBackend(seed=42),
        n_runs=5,
        shots=2048,
        metric_fn=lambda res: sum(v for k, v in res.counts.items() if k.count("1") >= 2) / 2048,
    )
    assert rep.summary.n == 5
    assert 0.0 <= rep.summary.cv_percent < 5.0


def test_scaling_sweep_logical_and_growth():
    def build(n):
        qc, _ = build_grover_circuit(n, 2, 1, initial_state="uniform")
        return qc

    report = sweep_item_counts(build, [3, 4, 5], transpile_circuits=False)
    depths = [r.logical_depth for r in report.results] if hasattr(report, "results") else None
    assert depths is not None and depths == sorted(depths)
    factors = growth_factors(report, field="logical_depth")
    assert len(factors) == 2 and all(f > 1 for f in factors)


def test_run_repeats_same_circuit_different_shot_noise():
    """Repeats share one transpiled circuit and differ only in the sampling seed."""
    qc, _ = build_grover_circuit(3, 0, 1, initial_state="uniform", marked_states=[3])
    backend = NoisySimulatorBackend(seed=7, optimization_level=3)
    a = backend.run_repeats(qc, 1024, [1, 2])
    again = backend.run_repeats(qc, 1024, [1])
    assert a[0].counts != a[1].counts          # different seeds -> different samples
    assert a[0].counts == again[0].counts      # same seed -> identical sample
    assert all(sum(x.counts.values()) == 1024 for x in a)
