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


# ---- manifest-driven budget and preregistration hash (no network, no submission) ----

def _fake_hardware(monkeypatch, tmp_path, **manifest_kw):
    """HardwareBackend with the IBM service and sampler mocked; calls records each submission's shots."""
    import qiskit_ibm_runtime
    from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

    calls = []
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "dummy-token-for-test")

    class FakeJob:
        def job_id(self):
            return "job-test"

        def result(self):
            class D:
                class data:
                    class c:
                        @staticmethod
                        def get_counts():
                            return {"00000": 1}
            return [D]

    class FakeSampler:
        class options:
            class dynamical_decoupling:
                enable = False
                sequence_type = ""

        def __init__(self, mode):
            pass

        def run(self, pubs, shots):
            calls.append(shots)
            return FakeJob()

    class FakeService:
        def __init__(self, **kw):
            pass

        def backend(self, name):
            return FakeMarrakesh()

    monkeypatch.setattr(qiskit_ibm_runtime, "QiskitRuntimeService", FakeService)
    monkeypatch.setattr(qiskit_ibm_runtime, "SamplerV2", FakeSampler)
    path = tmp_path / "m.json"
    write_campaign_manifest(str(path), {"x": 0.5}, **manifest_kw)
    return HardwareBackend(manifest_path=str(path)), calls


def test_shot_count_and_cap_come_from_the_manifest(monkeypatch, tmp_path, uniform_circuit):
    hb, calls = _fake_hardware(monkeypatch, tmp_path, max_jobs=2, shots=1000)
    with pytest.raises(ValueError, match="1000"):
        hb.run(uniform_circuit, shots=8192)
    hb.run(uniform_circuit, shots=1000)
    hb.run(uniform_circuit, shots=1000)
    assert calls == [1000, 1000]
    with pytest.raises(RuntimeError, match="Job cap reached: 2"):
        hb.run(uniform_circuit, shots=1000)


def test_manifest_without_budget_falls_back_to_legacy_limits(monkeypatch, tmp_path, uniform_circuit):
    hb, calls = _fake_hardware(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="8192"):
        hb.run(uniform_circuit, shots=1000)
    hb.run(uniform_circuit, shots=8192)
    assert calls == [8192]


def test_manifest_hash_is_stable_and_detects_edits(tmp_path):
    import json

    from qfim_bench.backends import manifest_hash, verify_manifest_hash

    path = tmp_path / "m.json"
    write_campaign_manifest(str(path), {"a": 1, "b": 2}, max_jobs=3, shots=4096, preregistration={"k": [1, 2]})
    m = json.loads(path.read_text())
    assert verify_manifest_hash(m)
    reordered = {k: m[k] for k in reversed(list(m))}
    reordered["jobs"] = [{"job_id": "x"}]  # job bookkeeping must not change the hash
    assert manifest_hash(reordered) == m["sha256"]
    m["predictions"]["a"] = 99  # editing a prediction must
    assert not verify_manifest_hash(m)
    assert not verify_manifest_hash({"predictions": {"a": 1}})  # no hash recorded
