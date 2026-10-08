"""Hardware safety rules. None of these tests contact IBM Quantum or submit a job."""

import pytest

from qfim_bench.backends import HardwareBackend, write_campaign_manifest
from qfim_bench.circuit import build_grover_circuit


@pytest.fixture
def uniform_circuit():
    qc, _ = build_grover_circuit(5, 2, 1, initial_state="uniform")
    return qc


def test_write_campaign_manifest_is_write_once(tmp_path):
    path = tmp_path / "m.json"
    write_campaign_manifest(str(path), {"r=1": 0.05})
    with pytest.raises(FileExistsError):
        write_campaign_manifest(str(path), {"r=1": 0.99})


def test_real_submission_refused_without_manifest(tmp_path, uniform_circuit, monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    hb = HardwareBackend(manifest_path=str(tmp_path / "missing.json"))
    with pytest.raises(RuntimeError):
        hb.run(uniform_circuit, shots=8192)


def test_real_submission_refused_without_token(tmp_path, uniform_circuit, monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    path = tmp_path / "m.json"
    write_campaign_manifest(str(path), {"r=1": 0.05})
    hb = HardwareBackend(manifest_path=str(path))
    with pytest.raises(RuntimeError, match="IBM_QUANTUM_TOKEN"):
        hb.run(uniform_circuit, shots=8192)


def test_parameterised_circuit_rejected(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    qc, _ = build_grover_circuit(5, 2, 1, initial_state="ansatz")  # bound, so no parameters
    from qiskit.circuit import Parameter
    from qiskit import QuantumCircuit

    bad = QuantumCircuit(1)
    bad.rx(Parameter("t"), 0)
    with pytest.raises(ValueError, match="unbound"):
        HardwareBackend(dry_run=True).run(bad, shots=8192)


def test_dry_run_reports_without_submitting(uniform_circuit, monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    hb = HardwareBackend(dry_run=True)
    res = hb.run(uniform_circuit, shots=8192)
    assert res.counts == {}
    assert hb.last_report["submitted"] is False
    assert hb.last_report["transpiled_depth"] > 0
    assert "fallback" in hb.last_report["target"] or "FakeMarrakesh" in hb.last_report["target"]


def test_instance_is_forwarded_to_the_service_when_given(monkeypatch):
    """Mocked: no network, no credentials. The instance CRN must reach QiskitRuntimeService."""
    import qiskit_ibm_runtime

    seen = {}

    class FakeService:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    monkeypatch.setattr(qiskit_ibm_runtime, "QiskitRuntimeService", FakeService)
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "dummy-token-for-test")

    HardwareBackend(instance="crn:v1:example")._service()
    assert seen["instance"] == "crn:v1:example"
    assert seen["channel"] == "ibm_quantum_platform"

    seen.clear()
    HardwareBackend()._service()
    assert "instance" not in seen
