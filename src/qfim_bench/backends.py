"""
backends.py: execution backends for qfim-bench.

One interface (`Backend.run`) is shared by every execution target, so the rest of the pipeline (and
noise_analysis.py / reproducibility.py) never has to know whether a circuit ran on a simulator or
on real hardware.

SimulatorBackend and NoisySimulatorBackend need no credentials and are the default path. The
noisy simulator uses the calibration snapshot FakeMarrakesh from qiskit-ibm-runtime, which is a
core dependency.

HardwareBackend submits to IBM Quantum through SamplerV2 in backend mode. It needs an API key in
the IBM_QUANTUM_TOKEN environment variable (this package's own convention; the key is passed to
QiskitRuntimeService explicitly) and, optionally, an instance CRN. Passing `instance` avoids a
search across every instance on each call. Submission is refused unless a campaign manifest with
predictions already exists and the job cap has not been reached; dry_run=True transpiles and
reports without submitting anything.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from qiskit import QuantumCircuit


# --------------------------------------------------------------------------
# Shared result type
# --------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    counts: dict[str, int]     # bitstring -> shot count, Qiskit-style
    shots: int
    backend_name: str


# --------------------------------------------------------------------------
# Abstract interface
# --------------------------------------------------------------------------

class Backend(ABC):
    """
    Every backend exposes exactly one method: run(circuit, shots) ->
    ExecutionResult. Nothing else in qfim-bench should call simulator- or
    hardware-specific APIs directly — always go through this interface, so
    swapping backends never requires touching pipeline, noise_analysis, or
    reproducibility code.
    """

    name: str

    @abstractmethod
    def run(self, circuit: QuantumCircuit, shots: int) -> ExecutionResult:
        raise NotImplementedError


# --------------------------------------------------------------------------
# Simulator backends (default — no credentials required)
# --------------------------------------------------------------------------

class SimulatorBackend(Backend):
    """
    Ideal, noiseless statevector/shot simulation via Qiskit Aer. This is
    the default backend for qfim-bench — installable and runnable with
    zero external accounts, API tokens, or network access beyond the
    initial `pip install qiskit-aer`.
    """

    name = "aer_simulator"

    def __init__(self, seed: int | None = None):
        from qiskit_aer import AerSimulator
        self._sim = AerSimulator(seed_simulator=seed)

    def run(self, circuit: QuantumCircuit, shots: int) -> ExecutionResult:
        job = self._sim.run(circuit, shots=shots)
        result = job.result()
        counts = result.get_counts()
        return ExecutionResult(counts=counts, shots=shots, backend_name=self.name)


class NoisySimulatorBackend(Backend):
    """
    Noisy simulation using a Qiskit calibration-snapshot "fake backend"
    (e.g. FakeMarrakesh, matching the companion paper's noise-attribution
    experiment), or any explicit qiskit_aer.noise.NoiseModel the caller
    supplies. Still requires no IBM Quantum account or network access —
    the fake-backend calibration data ships with qiskit-ibm-runtime's
    fake_provider module.

    This backend is what makes noise_analysis.compare_distributions()
    useful without ever touching real hardware: ideal vs. noisy-simulated
    vs. (optionally, later) real-hardware distributions can all be
    compared, with only the last one costing QPU time.
    """

    name = "noisy_simulator"

    def __init__(
        self,
        fake_backend_name: str = "FakeMarrakesh",
        seed: int | None = None,
        optimization_level: int | None = 3,
    ):
        """
        optimization_level defaults to 3, the level HardwareBackend uses, so a noisy-simulator
        circuit and a hardware circuit are transpiled the same way and can be compared. Pass 1 to
        reproduce the archived v1 noisy-simulation numbers (examples/precompute_noisy_sim.py does),
        or None for Qiskit's own default.
        """
        from qiskit_aer import AerSimulator
        from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

        _FAKE_BACKENDS = {"FakeMarrakesh": FakeMarrakesh}
        if fake_backend_name not in _FAKE_BACKENDS:
            raise ValueError(
                f"Unknown fake_backend_name '{fake_backend_name}'. "
                f"Available: {list(_FAKE_BACKENDS)}. "
                "Add more entries to _FAKE_BACKENDS in backends.py as needed."
            )

        fake_backend = _FAKE_BACKENDS[fake_backend_name]()
        self._sim = AerSimulator.from_backend(fake_backend)
        self.name = f"noisy_simulator[{fake_backend_name}]"
        self._seed = seed
        self._optimization_level = optimization_level

    def _transpile(self, circuit: QuantumCircuit):
        from qiskit import transpile

        kwargs = {"seed_transpiler": self._seed}
        if self._optimization_level is not None:
            kwargs["optimization_level"] = self._optimization_level
        return transpile(circuit, self._sim, **kwargs)

    def run(self, circuit: QuantumCircuit, shots: int) -> ExecutionResult:
        transpiled = self._transpile(circuit)
        job = self._sim.run(transpiled, shots=shots, seed_simulator=self._seed)
        result = job.result()
        counts = result.get_counts()
        return ExecutionResult(counts=counts, shots=shots, backend_name=self.name)

    def run_repeats(
        self, circuit: QuantumCircuit, shots: int, seeds: list[int]
    ) -> list[ExecutionResult]:
        """
        Transpile once, then sample once per simulator seed. Repeats differ only in shot noise
        (the transpiled circuit is identical), which is what a repeat-run study needs, and it
        avoids paying the transpile cost per repeat.
        """
        return self.sample(self._transpile(circuit), shots, seeds)

    def transpile(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Transpile exactly as run() does (target FakeMarrakesh, this backend's optimization level)."""
        return self._transpile(circuit)

    def sample(self, transpiled: QuantumCircuit, shots: int, seeds: list[int]) -> list[ExecutionResult]:
        """Sample an already transpiled circuit once per simulator seed."""
        results = []
        for seed in seeds:
            counts = self._sim.run(transpiled, shots=shots, seed_simulator=seed).result().get_counts()
            results.append(ExecutionResult(counts=counts, shots=shots, backend_name=self.name))
        return results


# --------------------------------------------------------------------------
# Hardware backend — NOT implemented yet (Step 10 of the build plan)
# --------------------------------------------------------------------------

class HardwareBackend(Backend):
    """
    Real IBM Quantum hardware via qiskit-ibm-runtime SamplerV2 in backend mode.

    Settings mirror the companion paper's hardware protocol: optimization level 3
    with a fixed transpiler seed, dynamical decoupling (XpXm), and 8192 shots.

    Safety rules, enforced in code rather than by convention:
      * dry_run=True transpiles against the target and reports depth and gate
        counts. Nothing is submitted and no QPU time is used.
      * A real submission is refused unless a campaign manifest already exists
        and holds the theoretical predictions, so predictions are always recorded
        before any job runs.
      * At most max_jobs jobs may be submitted through one manifest (default 5,
        matching the original r=1..4 plus one repeat design).
      * The circuit must have no free parameters (the uniform start has none).

    The token is read from the IBM_QUANTUM_TOKEN environment variable only.
    """

    name = "ibm_hardware"

    def __init__(
        self,
        backend_name: str = "ibm_marrakesh",
        dry_run: bool = False,
        max_jobs: int = 5,
        manifest_path: str | None = None,
        instance: str | None = None,
        optimization_level: int = 3,
        seed_transpiler: int = 42,
        dd_sequence: str = "XpXm",
    ):
        self.backend_name = backend_name
        self.dry_run = dry_run
        self.max_jobs = max_jobs
        self.manifest_path = manifest_path
        self.instance = instance
        self.optimization_level = optimization_level
        self.seed_transpiler = seed_transpiler
        self.dd_sequence = dd_sequence
        self.label = ""  # campaign label (e.g. "r=2 (repeat)"), recorded with each job
        self.last_report: dict | None = None

    # ---- target resolution ------------------------------------------------

    def _service(self):
        from qiskit_ibm_runtime import QiskitRuntimeService

        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if not token:
            raise RuntimeError("IBM_QUANTUM_TOKEN is not set; cannot reach IBM Quantum.")
        kwargs = {"instance": self.instance} if self.instance else {}
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, **kwargs)

    def _target(self):
        """Return (backend_object, target_label). Dry runs fall back to a local calibration snapshot."""
        try:
            return self._service().backend(self.backend_name), f"{self.backend_name} (live calibration)"
        except RuntimeError:
            if not self.dry_run:
                raise
            from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

            return FakeMarrakesh(), "FakeMarrakesh (local snapshot; no token, live calibration not checked)"

    # ---- transpilation shared by dry run and submission -------------------

    def _transpile(self, circuit: QuantumCircuit, backend) -> QuantumCircuit:
        from qiskit import transpile

        return transpile(
            circuit,
            backend=backend,
            optimization_level=self.optimization_level,
            seed_transpiler=self.seed_transpiler,
        )

    @staticmethod
    def _require_no_parameters(circuit: QuantumCircuit) -> None:
        if circuit.parameters:
            raise ValueError(
                f"circuit has {len(circuit.parameters)} unbound parameters; bind them before hardware use"
            )

    # ---- manifest ----------------------------------------------------------

    def _load_manifest(self) -> dict:
        import json

        if not self.manifest_path or not os.path.exists(self.manifest_path):
            raise RuntimeError(
                "No campaign manifest. Write predictions with write_campaign_manifest() before submitting."
            )
        with open(self.manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        if not manifest.get("predictions"):
            raise RuntimeError("Campaign manifest has no predictions; refusing to submit.")
        return manifest

    def _save_manifest(self, manifest: dict) -> None:
        import json

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    # ---- public API --------------------------------------------------------

    def run(self, circuit: QuantumCircuit, shots: int) -> ExecutionResult:
        self._require_no_parameters(circuit)
        backend, target_label = self._target()
        transpiled = self._transpile(circuit, backend)

        if self.dry_run:
            self.last_report = {
                "target": target_label,
                "logical_depth": circuit.depth(),
                "logical_gates": sum(circuit.count_ops().values()),
                "transpiled_depth": transpiled.depth(),
                "transpiled_gates": sum(transpiled.count_ops().values()),
                "two_qubit_gates": sum(v for k, v in transpiled.count_ops().items() if k in ("cz", "ecr", "cx")),
                "submitted": False,
            }
            return ExecutionResult(counts={}, shots=0, backend_name=f"{self.backend_name}:dry-run")

        manifest = self._load_manifest()
        if len(manifest.get("jobs", [])) >= self.max_jobs:
            raise RuntimeError(f"Job cap reached: {self.max_jobs} jobs already submitted for this manifest.")
        if shots != 8192:
            raise ValueError("this campaign is fixed at 8192 shots to match the original protocol")

        from qiskit_ibm_runtime import SamplerV2

        sampler = SamplerV2(mode=backend)
        sampler.options.dynamical_decoupling.enable = True
        sampler.options.dynamical_decoupling.sequence_type = self.dd_sequence

        job = sampler.run([transpiled], shots=shots)
        manifest["jobs"] = manifest.get("jobs", []) + [
            {"label": self.label, "job_id": job.job_id(), "target": target_label}
        ]
        self._save_manifest(manifest)  # record the job id before waiting on it

        result = job.result()
        counts = result[0].data.c.get_counts()
        return ExecutionResult(counts=dict(counts), shots=shots, backend_name=self.backend_name)


def write_campaign_manifest(path: str, predictions: dict[str, float], note: str = "") -> None:
    """
    Record predictions for a hardware campaign before any job is submitted.
    Refuses to overwrite an existing manifest, so predictions cannot be edited
    after data exists.
    """
    import datetime
    import json

    if os.path.exists(path):
        raise FileExistsError(f"{path} exists; predictions are write-once")
    manifest = {
        "written_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": note,
        "predictions": predictions,
        "jobs": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


# --------------------------------------------------------------------------
# Convenience factory
# --------------------------------------------------------------------------

def get_backend(name: str, **kwargs) -> Backend:
    """
    Construct a backend by name, e.g. get_backend("aer_simulator") or
    get_backend("noisy_simulator", fake_backend_name="FakeMarrakesh").
    Used by QFIMConfig.backend (a string) to resolve to an actual Backend
    instance in pipeline.py, so config stays a plain, serializable
    dataclass rather than holding live objects.
    """
    registry = {
        "aer_simulator": SimulatorBackend,
        "noisy_simulator": NoisySimulatorBackend,
        "ibm_hardware": HardwareBackend,
    }
    if name not in registry:
        raise ValueError(f"Unknown backend '{name}'. Available: {list(registry)}")
    return registry[name](**kwargs)
