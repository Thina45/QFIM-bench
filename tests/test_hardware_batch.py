"""Multi-circuit HardwareBackend mode. Fully mocked: no network, no credentials, no submission."""

import json

import pytest
import qiskit_ibm_runtime
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

from qfim_bench.backends import HardwareBackend, write_campaign_manifest
from qfim_bench.circuit import build_grover_circuit


def _circuits(k=3):
    return [build_grover_circuit(3, 0, r, initial_state="uniform", marked_states=[3], oracle_style="mcz")[0]
            for r in range(k)]


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """Returns make(usage_per_job=..., **manifest_kw) -> (backend, record); record collects submissions."""
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "dummy-token-for-test")

    def make(usage_per_job=None, metrics_quantum_seconds=None, **manifest_kw):
        record = {"n_pubs": [], "max_execution_time": []}

        class FakeJob:
            def job_id(self):
                return f"job-{len(record['n_pubs'])}"

            def usage(self):
                if usage_per_job is None:
                    raise AttributeError("not reported")
                return usage_per_job

            def metrics(self):
                if metrics_quantum_seconds is None:
                    raise AttributeError("not reported")
                return {"usage": {"quantum_seconds": metrics_quantum_seconds}}

            def result(self):
                n = record["n_pubs"][-1]

                class Pub:
                    class data:
                        class c:
                            @staticmethod
                            def get_counts():
                                return {"000": 5}
                return [Pub] * n

        class FakeSampler:
            class options:
                max_execution_time = None

                class dynamical_decoupling:
                    enable = False
                    sequence_type = ""

            def __init__(self, mode):
                pass

            def run(self, pubs, shots):
                record["n_pubs"].append(len(pubs))
                record["max_execution_time"].append(FakeSampler.options.max_execution_time)
                return FakeJob()

        class FakeService:
            def __init__(self, **kw):
                pass

            def backend(self, name):
                return FakeMarrakesh()

        monkeypatch.setattr(qiskit_ibm_runtime, "QiskitRuntimeService", FakeService)
        monkeypatch.setattr(qiskit_ibm_runtime, "SamplerV2", FakeSampler)
        path = tmp_path / f"m{len(list(tmp_path.iterdir()))}.json"
        write_campaign_manifest(str(path), {"x": 0.5}, shots=1000, **manifest_kw)
        record["sampler_options"] = FakeSampler.options
        return HardwareBackend(manifest_path=str(path)), record, path

    return make


def test_batch_is_one_job_with_one_pub_per_circuit_and_ordered_results(fake):
    hb, rec, path = fake(max_jobs=3)
    out = hb.run_batch(_circuits(3), shots=1000, labels=["a", "b", "c"])
    assert rec["n_pubs"] == [3] and len(out) == 3
    assert all(r.counts == {"000": 5} for r in out)
    job = json.loads(path.read_text())["jobs"][0]
    assert job["labels"] == ["a", "b", "c"] and job["n_circuits"] == 3


def test_billed_usage_is_recorded_per_job(fake):
    hb, _, path = fake(usage_per_job=12.5, max_jobs=5)
    hb.run_batch(_circuits(2), shots=1000)
    hb.run_batch(_circuits(2), shots=1000)
    m = json.loads(path.read_text())
    assert [j["usage_seconds"] for j in m["jobs"]] == [12.5, 12.5]
    assert hb.cumulative_usage_seconds() == 25.0


def test_metrics_quantum_seconds_is_preferred_over_a_stale_zero_from_usage(fake):
    """Regression: job.usage() has been observed to report 0 (not raise) right after
    job.result() returns, before the runtime finalizes billing -- metrics() is the
    source of truth and must win even when usage() returns a (wrong) value."""
    hb, _, path = fake(usage_per_job=0.0, metrics_quantum_seconds=20.0, max_jobs=1)
    hb.run_batch(_circuits(1), shots=1000)
    assert json.loads(path.read_text())["jobs"][0]["usage_seconds"] == 20.0


def test_unreported_usage_is_recorded_as_none(fake):
    hb, _, path = fake(max_jobs=2)
    hb.run_batch(_circuits(1), shots=1000)
    assert json.loads(path.read_text())["jobs"][0]["usage_seconds"] is None


def test_submission_aborts_once_cumulative_usage_reaches_the_budget(fake):
    hb, rec, _ = fake(usage_per_job=30.0, max_jobs=10, usage_budget_seconds=50.0)
    hb.run_batch(_circuits(1), shots=1000)  # 30 s used, under 50
    hb.run_batch(_circuits(1), shots=1000)  # 60 s used, now over
    with pytest.raises(RuntimeError, match="Usage budget reached"):
        hb.run_batch(_circuits(1), shots=1000)
    assert len(rec["n_pubs"]) == 2  # the refused call never reached the sampler


def test_max_job_seconds_is_passed_to_the_runtime(fake):
    hb, rec, _ = fake(max_jobs=2, max_job_seconds=40)
    hb.run_batch(_circuits(1), shots=1000)
    assert rec["max_execution_time"] == [40]


def test_batch_respects_shots_and_job_cap(fake):
    hb, _, _ = fake(max_jobs=1)
    with pytest.raises(ValueError, match="1000"):
        hb.run_batch(_circuits(1), shots=8192)
    hb.run_batch(_circuits(1), shots=1000)
    with pytest.raises(RuntimeError, match="Job cap reached"):
        hb.run_batch(_circuits(1), shots=1000)


def test_dd_enabled_defaults_to_true_and_sets_the_sequence(fake):
    hb, rec, _ = fake(max_jobs=1)
    hb.run_batch(_circuits(1), shots=1000)
    assert rec["sampler_options"].dynamical_decoupling.enable is True
    assert rec["sampler_options"].dynamical_decoupling.sequence_type == "XpXm"


def test_dd_enabled_false_disables_dynamical_decoupling(fake):
    hb, rec, _ = fake(max_jobs=1)
    hb.dd_enabled = False
    hb.run_batch(_circuits(1), shots=1000)
    assert rec["sampler_options"].dynamical_decoupling.enable is False


def test_initial_layout_is_passed_to_transpile(fake, monkeypatch):
    hb, _, _ = fake(max_jobs=1)
    hb.initial_layout = [10, 20, 30]
    seen = {}
    import qiskit as qiskit_module
    real_transpile = qiskit_module.transpile

    def spy_transpile(circuit, **kwargs):
        seen["initial_layout"] = kwargs.get("initial_layout")
        return real_transpile(circuit, **kwargs)

    monkeypatch.setattr(qiskit_module, "transpile", spy_transpile)
    hb.run_batch(_circuits(1), shots=1000)
    assert seen["initial_layout"] == [10, 20, 30]


def test_qpy_dir_saves_transpiled_circuits_with_recorded_hashes(fake, tmp_path):
    qpy_dir = tmp_path / "qpy"
    hb, _, path = fake(max_jobs=1)
    hb.qpy_dir = str(qpy_dir)
    hb.label = "batch1"
    hb.run_batch(_circuits(2), shots=1000, labels=["x", "y"])
    job = json.loads(path.read_text())["jobs"][0]
    assert len(job["qpy_files"]) == 2
    for entry, label in zip(job["qpy_files"], ["x", "y"]):
        assert entry["label"] == label
        saved = __import__("pathlib").Path(entry["path"])
        assert saved.exists()
        import hashlib
        assert hashlib.sha256(saved.read_bytes()).hexdigest() == entry["sha256"]


def test_batch_dry_run_reports_each_circuit_and_submits_nothing(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    hb = HardwareBackend(dry_run=True)
    out = hb.run_batch(_circuits(3), shots=1000)
    assert len(out) == 3 and hb.last_report["submitted"] is False
    counts = [c["two_qubit_gates"] for c in hb.last_report["circuits"]]
    assert counts[0] == 0 and counts == sorted(counts)


def test_empty_batch_rejected():
    with pytest.raises(ValueError):
        HardwareBackend(dry_run=True).run_batch([], shots=1000)
