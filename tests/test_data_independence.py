"""The cardinality oracle never sees the data; the data-driven oracle does (task a, STOP-GATE 2).

Two structurally different datasets (independent items vs themed co-occurrence) are run with
identical n, threshold, r, seed and shots.
"""

import random

import pytest

from qfim_bench.config import QFIMConfig
from qfim_bench.pipeline import run_qfim_bench

ITEMS = [f"item_{i}" for i in range(8)]


def _independent(path, seed=1, n_tx=300):
    rng = random.Random(seed)
    weights = [0.45, 0.40, 0.35, 0.30, 0.28, 0.10, 0.10, 0.08]
    rows = []
    for _ in range(n_tx):
        k = rng.randint(1, 5)
        basket = set()
        while len(basket) < k:
            basket.add(rng.choices(ITEMS, weights=weights)[0])
        rows.append(",".join(sorted(basket)))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _themed(path, seed=2, n_tx=300):
    rng = random.Random(seed)
    themes = [ITEMS[0:3], ITEMS[3:6]]
    rows = []
    for _ in range(n_tx):
        theme = rng.choice(themes)
        basket = {i for i in theme if rng.random() < 0.8}
        if rng.random() < 0.15:
            basket.add(rng.choice(ITEMS))
        if not basket:
            basket.add(rng.choice(theme))
        rows.append(",".join(sorted(basket)))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


@pytest.fixture(scope="module")
def datasets(tmp_path_factory):
    d = tmp_path_factory.mktemp("ds")
    a, b = d / "a.csv", d / "b.csv"
    _independent(a)
    _themed(b)
    return a, b


def _run(path, **kw):
    return run_qfim_bench(QFIMConfig(dataset_path=str(path), top_k_items=5, seed=42, **kw))


def test_cardinality_oracle_output_is_independent_of_the_dataset(datasets):
    a, b = datasets
    kw = dict(marking="cardinality", oracle_threshold=2, grover_iterations=2)
    assert _run(a, **kw).execution.counts == _run(b, **kw).execution.counts


def test_data_driven_oracle_output_depends_on_the_dataset(datasets):
    a, b = datasets
    kw = dict(marking="support", min_support=0.25, grover_iterations=None)
    ra, rb = _run(a, **kw), _run(b, **kw)
    assert ra.circuit_info.marked_indices != rb.circuit_info.marked_indices
    assert ra.execution.counts != rb.execution.counts
