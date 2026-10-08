"""
scaling.py — Stage 8 analysis module: directly measured (not estimated)
circuit-complexity scaling as candidate-item count increases.

Matches the companion paper's Section 6 practice exactly: circuits are
actually built (and, where practical within a time budget, transpiled) at
each item count, rather than extrapolated from a formula. A transpilation
that does not complete within the given time budget is recorded as an
explicit non-completion (budget_exceeded=True), never silently dropped or
replaced with an estimated value — matching the paper's own statement that
"15-item transpilation did not complete within budget and is reported as a
non-completion, not an estimate."

This module is circuit-agnostic: it takes a `build_circuit_fn(n_items) ->
QuantumCircuit` callable, so it can sweep item count for the QFIM oracle
circuit (via a small wrapper around circuit.build_grover_circuit) or for
any other parametrized circuit family a user supplies.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from qiskit import QuantumCircuit
    from qiskit.providers import BackendV2


@dataclass
class ItemCountResult:
    n_items: int
    logical_depth: int
    logical_gate_count: int
    logical_build_seconds: float
    transpiled_depth: int | None = None
    transpiled_gate_count: int | None = None
    transpile_seconds: float | None = None
    transpile_attempted: bool = False
    transpile_budget_exceeded: bool = False


@dataclass
class ScalingReport:
    results: list[ItemCountResult]


def _count_gates(circuit: "QuantumCircuit") -> int:
    """Total gate count = sum of all operation counts in the circuit."""
    return sum(circuit.count_ops().values())


def _transpile_with_timeout(
    circuit: "QuantumCircuit",
    backend: "BackendV2 | None",
    basis_gates: list[str] | None,
    optimization_level: int,
    seed_transpiler: int | None,
    timeout_seconds: float,
):
    """
    Run qiskit.transpile in a worker thread with a hard wall-clock
    timeout, so a transpilation that would run indefinitely (as the
    companion paper encountered at 15 items) can be reported as a
    non-completion rather than hanging the whole sweep. Returns
    (transpiled_circuit, elapsed_seconds) on success, or (None, None) on
    timeout.

    Uses a thread, not a process, so it shares memory with the caller
    (no pickling of the circuit object needed) — the timeout is
    best-effort (the underlying transpile call is not forcibly killed,
    only abandoned), which is an accepted tradeoff for a benchmarking
    tool: the thread may continue consuming CPU in the background after
    timeout, but the sweep itself proceeds to the next item count rather
    than blocking.
    """
    from qiskit import transpile

    def _do_transpile():
        start = time.perf_counter()
        result = transpile(
            circuit,
            backend=backend,
            basis_gates=basis_gates,
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )
        elapsed = time.perf_counter() - start
        return result, elapsed

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_transpile)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            return None, None


def sweep_item_counts(
    build_circuit_fn: Callable[[int], "QuantumCircuit"],
    item_counts: list[int],
    transpile_circuits: bool = True,
    transpile_backend: "BackendV2 | None" = None,
    basis_gates: list[str] | None = None,
    optimization_level: int = 3,
    seed_transpiler: int | None = 42,
    transpile_timeout_seconds: float = 120.0,
) -> ScalingReport:
    """
    For each n in item_counts: build the circuit via build_circuit_fn(n),
    measure its logical depth and gate count, and — if
    transpile_circuits is True — attempt transpilation against
    transpile_backend (or basis_gates directly if no backend object is
    available) with a wall-clock budget of transpile_timeout_seconds,
    recording transpiled depth/gate count on success or
    transpile_budget_exceeded=True on timeout.

    item_counts should be given in ascending order; the sweep does not
    stop early on a timeout — it proceeds to the next item count, since a
    later (larger) item count may still be worth attempting, or the
    caller may want the logical-only numbers for it even when transpile
    isn't feasible, exactly matching the companion paper's practice of
    reporting 15-item logical numbers alongside a 15-item
    transpile-non-completion.
    """
    if not item_counts:
        raise ValueError("item_counts must be non-empty")

    results = []
    for n in item_counts:
        start = time.perf_counter()
        circuit = build_circuit_fn(n)
        logical_build_seconds = time.perf_counter() - start

        logical_depth = circuit.depth()
        logical_gate_count = _count_gates(circuit)

        result = ItemCountResult(
            n_items=n,
            logical_depth=logical_depth,
            logical_gate_count=logical_gate_count,
            logical_build_seconds=logical_build_seconds,
        )

        if transpile_circuits:
            result.transpile_attempted = True
            transpiled, elapsed = _transpile_with_timeout(
                circuit,
                backend=transpile_backend,
                basis_gates=basis_gates,
                optimization_level=optimization_level,
                seed_transpiler=seed_transpiler,
                timeout_seconds=transpile_timeout_seconds,
            )
            if transpiled is None:
                result.transpile_budget_exceeded = True
            else:
                result.transpiled_depth = transpiled.depth()
                result.transpiled_gate_count = _count_gates(transpiled)
                result.transpile_seconds = elapsed

        results.append(result)

    return ScalingReport(results=results)


def growth_factors(report: ScalingReport, field: str = "logical_gate_count") -> list[float]:
    """
    Convenience: ratio of `field` between each consecutive pair of results
    in the sweep, e.g. growth_factors(report) on a [5,10,15]-item sweep
    returns [gate_count(10)/gate_count(5), gate_count(15)/gate_count(10)]
    — reproduces the companion paper's "roughly 34x from 5 to 10 items
    and a further 32x from 10 to 15" statement directly from measured
    data, for any field (logical_depth, logical_gate_count,
    transpiled_depth, transpiled_gate_count).

    A None value (e.g. transpiled_gate_count after a budget-exceeded
    result) produces a None entry in the output rather than raising, so a
    partially-transpiled sweep still yields growth factors for the fields
    that did complete.
    """
    values = [getattr(r, field) for r in report.results]
    factors = []
    for prev, curr in zip(values, values[1:]):
        if prev is None or curr is None or prev == 0:
            factors.append(None)
        else:
            factors.append(curr / prev)
    return factors


# --------------------------------------------------------------------------
# Oracle accounting and item-count sweep with a hard (process-killing) timeout
# --------------------------------------------------------------------------

import multiprocessing as _mp
import queue as _queue

_TWO_QUBIT_GATES = ("cz", "cx", "ecr")


def _transpile_worker(out, circuit, basis_gates, backend_name, optimization_level, seed):
    """Runs in a child process so a timeout can kill it."""
    try:
        from qiskit import transpile

        t0 = time.perf_counter()
        if backend_name == "FakeMarrakesh":
            from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

            tc = transpile(circuit, backend=FakeMarrakesh(), optimization_level=optimization_level,
                           seed_transpiler=seed)
        else:
            tc = transpile(circuit, basis_gates=basis_gates, optimization_level=optimization_level,
                           seed_transpiler=seed)
        ops = tc.count_ops()
        out.put(("ok", {
            "depth": tc.depth(),
            "gates": int(sum(ops.values())),
            "two_qubit_gates": int(sum(v for k, v in ops.items() if k in _TWO_QUBIT_GATES)),
            "seconds": time.perf_counter() - t0,
        }))
    except Exception as exc:  # reported to the parent, never swallowed
        out.put(("error", f"{type(exc).__name__}: {exc}"))


def transpile_hard_timeout(
    circuit: "QuantumCircuit",
    timeout_seconds: float,
    *,
    backend_name: str | None = None,
    basis_gates: list[str] | None = None,
    optimization_level: int = 1,
    seed: int = 42,
) -> dict:
    """
    Transpile in a child process and terminate it if it exceeds timeout_seconds. Returns
    {"status": "ok", depth, gates, two_qubit_gates, seconds}, {"status": "timeout"} or
    {"status": "error", "error": ...}. A timeout is a recorded non-completion, never an estimate.

    backend_name="FakeMarrakesh" transpiles to that device (routing included); otherwise the
    circuit is transpiled all-to-all to `basis_gates` (default cz, id, rz, sx, x), which isolates
    the circuit's own cost from connectivity.
    """
    basis = basis_gates or ["cz", "id", "rz", "sx", "x"]
    ctx = _mp.get_context("spawn")
    out = ctx.Queue()
    proc = ctx.Process(
        target=_transpile_worker,
        args=(out, circuit, basis, backend_name, optimization_level, seed),
        daemon=True,
    )
    proc.start()
    try:
        status, payload = out.get(timeout=timeout_seconds)
    except _queue.Empty:
        proc.terminate()
        proc.join()
        return {"status": "timeout", "timeout_seconds": timeout_seconds}
    proc.join()
    if status == "error":
        return {"status": "error", "error": payload}
    return {"status": "ok", **payload}


@dataclass
class OracleCost:
    """One row of the oracle-accounting / item-count tables (figure-ready via oracle_costs_to_dataframe)."""
    n_items: int
    M: int
    marking: str
    component: str  # "oracle" or "iteration" (oracle + diffusion)
    target: str     # "all_to_all" or a device name
    logical_depth: int
    logical_gates: int
    transpile_status: str  # "ok", "timeout" or "error"
    transpiled_depth: int | None = None
    transpiled_gates: int | None = None
    transpiled_two_qubit_gates: int | None = None
    transpile_seconds: float | None = None


def oracle_costs(
    n_items: int,
    marked_indices: list[int],
    marking: str,
    *,
    components: tuple[str, ...] = ("oracle", "iteration"),
    targets: tuple[str, ...] = ("all_to_all",),
    timeout_seconds: float = 120.0,
) -> list[OracleCost]:
    """
    Logical and transpiled depth / gate / two-qubit-gate counts for the oracle alone and for one
    full Grover iteration (oracle + Hadamard diffusion, uniform start) with the given marked set.
    Each transpile has a hard timeout; a timeout is recorded explicitly.
    """
    from qiskit import QuantumCircuit

    from .circuit import build_diffusion, build_oracle_for_states

    rows = []
    oracle = build_oracle_for_states(n_items, marked_indices)
    for component in components:
        if component == "oracle":
            circuit = oracle
        elif component == "iteration":
            circuit = QuantumCircuit(n_items + 1)
            circuit.compose(oracle, inplace=True)
            circuit.compose(build_diffusion(n_items), qubits=range(n_items), inplace=True)
        else:
            raise ValueError(f"unknown component {component!r}")
        for target in targets:
            res = transpile_hard_timeout(
                circuit,
                timeout_seconds,
                backend_name=None if target == "all_to_all" else target,
            )
            row = OracleCost(
                n_items=n_items, M=len(marked_indices), marking=marking, component=component,
                target=target, logical_depth=circuit.depth(), logical_gates=_count_gates(circuit),
                transpile_status=res["status"],
            )
            if res["status"] == "ok":
                row.transpiled_depth = res["depth"]
                row.transpiled_gates = res["gates"]
                row.transpiled_two_qubit_gates = res["two_qubit_gates"]
                row.transpile_seconds = res["seconds"]
            rows.append(row)
    return rows


def oracle_costs_to_dataframe(rows: list[OracleCost]):
    """Figure-ready pandas DataFrame, one row per OracleCost."""
    import pandas as pd

    return pd.DataFrame([r.__dict__ for r in rows])
