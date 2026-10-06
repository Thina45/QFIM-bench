"""Save as tests/test_manifest.py."""

import json

import pytest

from qfim_bench.config import QFIMConfig
from qfim_bench.manifest import environment_info, write_experiment_manifest


def test_environment_info_has_expected_shape():
    env = environment_info()
    assert set(env.keys()) == {"captured_utc", "python", "platform", "git_commit", "packages"}
    for pkg in ("qiskit", "qiskit_aer", "numpy", "scipy", "pandas", "qfim_bench"):
        assert pkg in env["packages"]


def test_environment_info_reports_real_qiskit_version():
    env = environment_info()
    # In the real environment (not a sandbox without qiskit), these must
    # be real version strings, not None — this is the whole point of the
    # function, so a None here is worth investigating, not ignoring.
    assert env["packages"]["qiskit"] is not None
    assert env["packages"]["qfim_bench"] is not None


def test_write_experiment_manifest_round_trips_dataclass_config(tmp_path):
    cfg = QFIMConfig(dataset_path="data.csv", top_k_items=5, seed=42)
    path = tmp_path / "manifest.json"
    write_experiment_manifest(str(path), cfg, extra={"note": "unit test"})

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["config"]["dataset_path"] == "data.csv"
    assert loaded["config"]["seed"] == 42
    assert loaded["extra"]["note"] == "unit test"
    assert "environment" in loaded


def test_write_experiment_manifest_is_write_once_by_default(tmp_path):
    cfg = QFIMConfig(dataset_path="data.csv")
    path = tmp_path / "manifest.json"
    write_experiment_manifest(str(path), cfg)
    with pytest.raises(FileExistsError):
        write_experiment_manifest(str(path), cfg)
    write_experiment_manifest(str(path), cfg, overwrite=True)  # should not raise
