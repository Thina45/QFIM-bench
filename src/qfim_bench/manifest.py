"""
manifest.py — lightweight experiment manifest and environment capture.

This is deliberately NOT a CLI and NOT a reconstruction engine (that scope
was explicitly declined). It's two small, genuinely useful pieces of
reproducibility infrastructure:

  - environment_info() returns a dict describing the exact software
    environment a run executed in (package versions, Python, OS, git
    commit if available) — the kind of thing a reviewer or future-you
    needs to explain why a number changed between runs.

  - write_experiment_manifest(path, config, extra=None) writes a JSON
    manifest next to a pipeline run's results: the QFIMConfig used,
    environment_info(), and a timestamp. Refuses to overwrite an existing
    manifest unless overwrite=True — same write-once discipline as the
    hardware campaign manifest in backends.py, so a result's provenance
    can't be silently edited after the fact.

Typical use (add to examples/quickstart.py or any script producing a
result worth keeping):

    from qfim_bench.manifest import write_experiment_manifest
    write_experiment_manifest("results/run1/manifest.json", cfg)
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path


def _git_commit() -> str | None:
    """Short git commit hash of the current checkout, or None if unavailable
    (not a git repo, git not installed, etc. — never raises)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _package_version(module_name: str) -> str | None:
    """Best-effort __version__ lookup; None if the package isn't installed."""
    try:
        mod = __import__(module_name)
        return getattr(mod, "__version__", None)
    except ImportError:
        return None


def environment_info() -> dict:
    """
    Snapshot of the software environment, for inclusion in an experiment
    manifest. Every package field is best-effort: a package that isn't
    installed reports None rather than raising, so this can be called in
    a simulator-only environment without, say, qiskit-ibm-runtime.
    """
    return {
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_commit(),
        "packages": {
            "qiskit": _package_version("qiskit"),
            "qiskit_aer": _package_version("qiskit_aer"),
            "qiskit_ibm_runtime": _package_version("qiskit_ibm_runtime"),
            "numpy": _package_version("numpy"),
            "scipy": _package_version("scipy"),
            "pandas": _package_version("pandas"),
            "mlxtend": _package_version("mlxtend"),
            "qfim_bench": _package_version("qfim_bench"),
        },
    }


def _config_to_dict(config) -> dict:
    if is_dataclass(config):
        return asdict(config)
    if isinstance(config, dict):
        return config
    raise TypeError("config must be a dataclass instance (e.g. QFIMConfig) or a dict")


def write_experiment_manifest(
    path: str,
    config,
    extra: dict | None = None,
    overwrite: bool = False,
) -> dict:
    """
    Write a manifest JSON capturing the config used for a run plus the
    software environment, so a later reader (a reviewer, or future-you)
    can see exactly what produced a given result without re-deriving it
    from code or chat history.

    Raises FileExistsError if `path` already exists and overwrite=False.
    Returns the manifest dict that was written.
    """
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(f"{path} already exists; pass overwrite=True to replace it")

    manifest = {
        "config": _config_to_dict(config),
        "environment": environment_info(),
    }
    if extra:
        manifest["extra"] = extra

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest
