"""Hellinger distance: 0 for identical distributions, 1 for disjoint support."""

import numpy as np
import pytest

from qfim_bench.tvd_calibration import hellinger


def test_zero_for_identical_distributions():
    p = np.array([0.2, 0.3, 0.5])
    assert hellinger(p, p) == pytest.approx(0.0, abs=1e-12)


def test_one_for_disjoint_support():
    p = np.array([1.0, 0.0])
    q = np.array([0.0, 1.0])
    assert hellinger(p, q) == pytest.approx(1.0)


def test_hand_computed_two_outcome_example():
    p = np.array([0.8, 0.2])
    q = np.array([0.5, 0.5])
    # H = sqrt(1 - sqrt(0.8*0.5) - sqrt(0.2*0.5))
    expected = np.sqrt(1 - np.sqrt(0.4) - np.sqrt(0.1))
    assert hellinger(p, q) == pytest.approx(expected)


def test_symmetric():
    p = np.array([0.1, 0.4, 0.5])
    q = np.array([0.6, 0.1, 0.3])
    assert hellinger(p, q) == pytest.approx(hellinger(q, p))
