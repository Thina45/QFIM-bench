"""Item 5 of the CPC v4 pass: a calibration-snapshot digital twin for every saved calibration
snapshot used by a real campaign (Oct-8 ibm_marrakesh, Run 1 ibm_marrakesh, Run 3 ibm_marrakesh,
Run 4 ibm_kingston), compared against hardware and against the GENERIC fake-backend noisy
simulator, per cell (TVD, Hellinger). Read-only: backend.properties(datetime=...) queries only
(no job submitted); circuits transpiled locally and simulated locally with qiskit-aer.

Oct-8's twin already exists (results/cpc_revision/phase1e_digital_twin.json, built by
analysis/phase1e_digital_twin.py) and is reused here, not recomputed. This script builds Run 1,
Run 3 and Run 4's twins the same way: NoiseModel.from_backend_properties(props,
thermal_relaxation=False) -- this device's BackendProperties has no 'frequency' field, so the T1/T2
term cannot be included, same caveat as Oct-8's twin.

Transpilation matches how each session's REAL circuits were actually produced (REPORT.md section
9c): Run 1 and Run 4 re-transpiled fresh against live calibration each time (no pinned layout), so
the twin here also transpiles fresh (no initial_layout) -- seed_transpiler=42 reproduces the same
layout choice deterministically given the same live target. Run 3 pinned initial_layout per tier
(campaigns/cpc_run3/manifest.json), so the twin pins the same layout.

No generic "FakeKingston" ships with this qiskit-ibm-runtime version -- the generic-fake-backend
comparison column is N/A for Run 4 and reported as such, not filled in with a substitute.

    python analysis/digital_twins_v4.py
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ladder_predictions import marked_set  # noqa: E402

from qfim_bench.circuit import build_grover_circuit  # noqa: E402
from qfim_bench.tvd_calibration import hellinger, tvd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "cpc_v4"
OUT.mkdir(parents=True, exist_ok=True)
TIERS = {"A": (3, 1), "B": (4, 2), "C": (5, 4)}
SHOTS = 8192
SEED = 42

token = os.environ["IBM_QUANTUM_TOKEN"]
service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)


def hw_counts(pattern, label):
    import glob
    pooled = {}
    for fpath in sorted(glob.glob(str(ROOT / pattern))):
        d = json.loads(Path(fpath).read_text(encoding="utf-8"))
        if label in d["counts"]:
            for bit, c in d["counts"][label].items():
                pooled[bit] = pooled.get(bit, 0) + c
    return pooled


def dist(counts_a, counts_b):
    keys = sorted(set(counts_a) | set(counts_b))
    ta, tb = sum(counts_a.values()), sum(counts_b.values())
    pa = np.array([counts_a.get(k, 0) / ta for k in keys])
    pb = np.array([counts_b.get(k, 0) / tb for k in keys])
    return float(tvd(pa, pb)), float(hellinger(pa, pb))


def run_session(name, backend_name, calib_ts_by_tier, hw_pattern_by_tier, pinned_layout=None,
                generic_fake=None, offset_minutes=8):
    backend = service.backend(backend_name)
    rows = []
    for tier, (n, M) in TIERS.items():
        ts = datetime.fromisoformat(calib_ts_by_tier[tier])
        # historical-properties indexing lag: offset confirmed exact per-backend by binary search
        # (ibm_marrakesh: +8 min; ibm_kingston: +18 min -- different backends, different lag)
        props = backend.properties(datetime=ts + timedelta(minutes=offset_minutes))
        exact = str(props.last_update_date) == calib_ts_by_tier[tier]
        nm = NoiseModel.from_backend_properties(props, thermal_relaxation=False)
        sim_twin = AerSimulator(noise_model=nm)
        sim_generic = AerSimulator(noise_model=NoiseModel.from_backend(generic_fake)) if generic_fake else None

        layout = pinned_layout[tier] if pinned_layout else None
        for r in range(5):
            qc = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked_set(n, M),
                                       oracle_style="mcz")[0]
            kwargs = {"optimization_level": 3, "seed_transpiler": SEED}
            if layout is not None:
                kwargs["initial_layout"] = layout
            tq = transpile(qc, backend=backend, **kwargs)

            twin_counts = AerSimulator(noise_model=nm).run(tq, shots=SHOTS, seed_simulator=0).result().get_counts()
            label = f"ladder_n{n}_M{M}_r{r}"
            hwc = hw_counts(hw_pattern_by_tier[tier], label)
            tvd_twin, hel_twin = dist(hwc, twin_counts)

            row = {"tier": tier, "n": n, "r": r, "calibration_timestamp": calib_ts_by_tier[tier],
                   "exact_calibration_match": exact,
                   "tvd_hw_vs_digital_twin": tvd_twin, "hellinger_hw_vs_digital_twin": hel_twin}
            if sim_generic is not None:
                generic_counts = sim_generic.run(tq, shots=SHOTS, seed_simulator=0).result().get_counts()
                tvd_g, hel_g = dist(hwc, generic_counts)
                row["tvd_hw_vs_generic_fake"] = tvd_g
                row["hellinger_hw_vs_generic_fake"] = hel_g
            else:
                row["tvd_hw_vs_generic_fake"] = None
                row["hellinger_hw_vs_generic_fake"] = None
            rows.append(row)
            print(name, tier, r, "done")
    return rows


def main():
    out = {}

    out["Run1"] = run_session(
        "Run1", "ibm_marrakesh",
        calib_ts_by_tier={"A": "2026-11-19 14:35:58+05:30", "B": "2026-11-19 14:35:58+05:30",
                           "C": "2026-11-19 14:48:07+05:30"},
        hw_pattern_by_tier={"A": "results/hardware/cpc_run1/A_run*.json",
                             "B": "results/hardware/cpc_run1/B_run*.json",
                             "C": "results/hardware/cpc_run1/C_run*.json"},
        generic_fake=FakeMarrakesh(),
    )

    run3_manifest = json.loads((ROOT / "campaigns/cpc_run3/manifest.json").read_text())
    pinned = run3_manifest["preregistration"]["layout"]["pinned_layout_order"]
    out["Run3"] = run_session(
        "Run3", "ibm_marrakesh",
        calib_ts_by_tier={"A": "2026-11-20 03:39:26+05:30", "B": "2026-11-20 03:39:26+05:30",
                           "C": "2026-11-20 03:39:26+05:30"},
        hw_pattern_by_tier={"A": "results/hardware/cpc_run3/A_run*.json",
                             "B": "results/hardware/cpc_run3/B_run*.json",
                             "C": "results/hardware/cpc_run3/C_run*.json"},
        pinned_layout=pinned,
        generic_fake=FakeMarrakesh(),
    )

    out["Run4"] = run_session(
        "Run4", "ibm_kingston",
        calib_ts_by_tier={"A": "2026-11-19 05:36:23+05:30", "B": "2026-11-19 05:36:23+05:30",
                           "C": "2026-11-19 05:36:23+05:30"},
        hw_pattern_by_tier={"A": "results/hardware/cpc_run4/A_run*.json",
                             "B": "results/hardware/cpc_run4/B_run*.json",
                             "C": "results/hardware/cpc_run4/C_run*.json"},
        generic_fake=None,  # no FakeKingston in this qiskit-ibm-runtime version
        offset_minutes=18,
    )

    (OUT / "digital_twins_v4.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'digital_twins_v4.json'}")


if __name__ == "__main__":
    main()
