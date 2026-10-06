"""
tests/test_hardware_campaign_analysis.py — permanent regression test for
the noisy-simulator-vs-hardware comparison at every r in the uniform-start
campaign. Promotes the one-off scratch script (deleted after use) into a
real, repeatable check, using the fixed (seeded) NoisySimulatorBackend.

Skips cleanly if the campaign data isn't present in this checkout (it's
real hardware output, not something to regenerate casually — see
campaigns/uniform_marrakesh/).
"""

import json
from pathlib import Path

import pytest

from qfim_bench.backends import NoisySimulatorBackend
from qfim_bench.circuit import build_grover_circuit

CAMPAIGN_DIR = Path(__file__).resolve().parents[1] / "campaigns" / "uniform_marrakesh"


def _load_hw_empirical(r: int) -> float | None:
    f = CAMPAIGN_DIR / f"r{r}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    counts = d["counts"]
    total = sum(counts.values())
    marked = sum(c for bits, c in counts.items() if bits.count("1") >= 2)
    return marked / total


@pytest.mark.parametrize("r", [1, 2, 3, 4])
def test_noisy_simulator_within_tolerance_of_uniform_hardware(r):
    hw = _load_hw_empirical(r)
    if hw is None:
        pytest.skip(f"no campaign data for r={r} in this checkout")

    qc, _ = build_grover_circuit(5, 2, r, initial_state="uniform")
    counts = NoisySimulatorBackend(seed=42).run(qc, shots=8192).counts
    total = sum(counts.values())
    noisy = sum(c for bits, c in counts.items() if bits.count("1") >= 2) / total

    # The original comparison showed |noisy - hardware| <= ~0.012 at every
    # r. 0.03 gives headroom for a different seed/shot count while still
    # catching a real regression (e.g. the seeding bug reappearing, which
    # would make this flaky across repeated test runs rather than just
    # "off by a bit").
    assert abs(noisy - hw) < 0.03, f"r={r}: noisy={noisy:.4f} hardware={hw:.4f}"


def test_noisy_simulator_is_reproducible_across_two_calls():
    """
    Regression test for the NoisySimulatorBackend seeding bug: two calls
    with the same seed must return identical counts, not just similar
    ones. This is what actually broke before seed_simulator was added.
    """
    qc, _ = build_grover_circuit(5, 2, 2, initial_state="uniform")
    counts_a = NoisySimulatorBackend(seed=42).run(qc, shots=8192).counts
    counts_b = NoisySimulatorBackend(seed=42).run(qc, shots=8192).counts
    assert counts_a == counts_b
