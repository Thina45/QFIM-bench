"""Oracle accounting and the hard-timeout transpile (Phase 1 item 5)."""

import multiprocessing

from qiskit import QuantumCircuit

from qfim_bench.scaling import oracle_costs, oracle_costs_to_dataframe, transpile_hard_timeout


def _small_circuit():
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.ccx(0, 1, 2)
    return qc


def test_hard_timeout_completes_normally():
    res = transpile_hard_timeout(_small_circuit(), timeout_seconds=120)
    assert res["status"] == "ok"
    assert res["depth"] > 0 and res["two_qubit_gates"] > 0


def test_hard_timeout_kills_the_worker_and_reports_a_non_completion():
    """Starting a spawned worker takes longer than 0.05 s, so this must time out; the child must
    not be left running."""
    before = {p.pid for p in multiprocessing.active_children()}
    res = transpile_hard_timeout(_small_circuit(), timeout_seconds=0.05)
    assert res["status"] == "timeout"
    leftover = [p for p in multiprocessing.active_children() if p.pid not in before and p.is_alive()]
    assert leftover == []


def test_oracle_cost_grows_with_marked_set_size():
    rows = []
    for M in (1, 3):
        rows += oracle_costs(4, list(range(M)), f"explicit_M{M}", components=("oracle",), timeout_seconds=120)
    one, three = rows
    assert one.transpile_status == three.transpile_status == "ok"
    assert three.logical_gates > one.logical_gates
    assert three.transpiled_two_qubit_gates > one.transpiled_two_qubit_gates


def test_dataframe_is_figure_ready():
    rows = oracle_costs(3, [1], "explicit_M1", components=("oracle", "iteration"), timeout_seconds=120)
    df = oracle_costs_to_dataframe(rows)
    assert set(df["component"]) == {"oracle", "iteration"}
    assert {"n_items", "M", "transpiled_depth", "transpiled_two_qubit_gates", "transpile_status"} <= set(df.columns)
