"""Phase 1E: calibration-day digital twin (read-only properties fetch, local simulation only)."""
import json, os, datetime, sys
sys.path.insert(0, r"v:\D\Quantum programs\Quantum Apriori Algorithm\qfim-bench\src")
sys.path.insert(0, r"v:\D\Quantum programs\Quantum Apriori Algorithm\qfim-bench\analysis")

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_aer.noise import NoiseModel
from qiskit_aer import AerSimulator
from qiskit import transpile

from qfim_bench.circuit import build_grover_circuit
from qfim_bench.tvd_calibration import tvd, hellinger
from ladder_predictions import marked_set

ROOT = r"v:\D\Quantum programs\Quantum Apriori Algorithm\qfim-bench"
OUT = os.path.join(ROOT, "results", "cpc_revision")

token = os.environ["IBM_QUANTUM_TOKEN"]
service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
backend = service.backend("ibm_marrakesh")

windows = {
    "tierA": "2026-10-08 17:49:07+05:30",
    "tierB_tierC_run1-3": "2026-10-08 18:13:43+05:30",
    "tierC_run4-5": "2026-10-08 18:32:55+05:30",
}

TIERS = {"A": (3, 1), "B": (4, 2), "C": (5, 4)}
TIER_WINDOW = {"A": "tierA", "B": "tierB_tierC_run1-3", "C": "tierB_tierC_run1-3"}
# Tier C uses two windows; use run1-3's window as primary (3 of 5 runs), note the caveat.

props_cache = {}
for key, ts_str in windows.items():
    ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S%z")
    props_cache[key] = backend.properties(datetime=ts + datetime.timedelta(minutes=14))

import numpy as np
rows = []
for tier, (n, M) in TIERS.items():
    window_key = TIER_WINDOW[tier]
    props = props_cache[window_key]
    nm = NoiseModel.from_backend_properties(props, thermal_relaxation=False)
    sim = AerSimulator(noise_model=nm)
    for r in range(5):
        qc = build_grover_circuit(n, 0, r, initial_state="uniform", marked_states=marked_set(n, M), oracle_style="mcz")[0]
        tq = transpile(qc, backend=backend, optimization_level=3, seed_transpiler=42)
        shots = 8192
        result = sim.run(tq, shots=shots, seed_simulator=0).result()
        counts = result.get_counts()
        total = sum(counts.values())
        twin_probs = {k: v / total for k, v in counts.items()}

        # load the real hardware raw counts for this (tier, r) to compare
        import glob
        pattern = {
            "A": "results/hardware/ladder_v2/day*.json",
            "B": "results/hardware/ladder_v2b/B_run*.json",
            "C": "results/hardware/ladder_v2b/C_run*.json",
        }[tier]
        label = f"ladder_n{n}_M{M}_r{r}"
        pooled_counts = {}
        for fpath in sorted(glob.glob(os.path.join(ROOT, pattern))):
            d = json.load(open(fpath))
            if label in d["counts"]:
                for bit, c in d["counts"][label].items():
                    pooled_counts[bit] = pooled_counts.get(bit, 0) + c
        hw_total = sum(pooled_counts.values())
        hw_probs = {k: v / hw_total for k, v in pooled_counts.items()}

        keys = sorted(set(twin_probs) | set(hw_probs))
        p_twin = np.array([twin_probs.get(k, 0.0) for k in keys])
        p_hw = np.array([hw_probs.get(k, 0.0) for k in keys])
        rows.append({
            "tier": tier, "n": n, "r": r, "window": window_key,
            "tvd_hw_vs_digital_twin": float(tvd(p_hw, p_twin)),
            "hellinger_hw_vs_digital_twin": float(hellinger(p_hw, p_twin)),
        })
        print(tier, r, "done")

with open(os.path.join(OUT, "phase1e_digital_twin.json"), "w") as f:
    json.dump({
        "note": "Calibration-day digital twin: NoiseModel.from_backend_properties() on the exact live ibm_marrakesh BackendProperties at each campaign calibration timestamp (read-only query, re-fetched this pass via backend.properties(datetime=...)). qiskit-aer 0.17.2 has from_backend_properties available.",
        "caveat_tier_C": "Tier C runs 4-5 used a later calibration window (2026-10-08 18:32:55+05:30); this twin uses the run1-3 window (18:13:43+05:30) shared with Tier B, since 3 of 5 Tier C runs used it.",
        "rows": rows,
    }, f, indent=2)
print("saved phase1e_digital_twin.json")
