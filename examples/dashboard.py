"""
examples/dashboard.py — Streamlit demo for qfim-bench.

Run locally (from the qfim-bench root):
    pip install -e ".[dashboard]"
    streamlit run examples/dashboard.py

Deploy: push this repo to GitHub, then deploy at https://share.streamlit.io
pointing at examples/dashboard.py. requirements.txt lists every dependency.

Design rule: this app never calls HardwareBackend. Panels 1, 2 and 4 use the
simulator backends only. Panel 3 reads the five archived hardware results from
campaigns/uniform_marrakesh/*.json and never re-runs them, so no visitor can
spend QPU time or bypass the job cap in HardwareBackend.

Simulator results are cached with st.cache_data, so repeated page loads and
slider moves do not re-run identical simulations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from qfim_bench.backends import SimulatorBackend
from qfim_bench.circuit import build_grover_circuit
from qfim_bench.classical import brute_force_frequent_itemsets, run_classical_baseline
from qfim_bench.preprocessing import load_transactions, reduce_to_selected_items, select_top_k_items

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "data" / "sample_transactions.csv"
CAMPAIGN_DIR = ROOT / "campaigns" / "uniform_marrakesh"


@st.cache_data(show_spinner=False)
def noiseless_p(n_items: int, threshold: int, r: int, init: str) -> tuple[float, float]:
    """Return (theoretical_p, empirical_p) on the seeded noiseless simulator."""
    qc, info = build_grover_circuit(n_items, threshold, r, initial_state=init, seed=42)
    counts = SimulatorBackend(seed=42).run(qc, shots=8192).counts
    empirical = sum(c for b, c in counts.items() if b.count("1") >= threshold) / sum(counts.values())
    return info.theoretical_p, empirical


@st.cache_data(show_spinner=False)
def noisy_p(r: int) -> float | None:
    """Seeded FakeMarrakesh marked-state probability (uniform start, t=2, 5 items), from the precomputed file."""
    f = CAMPAIGN_DIR / "noisy_sim_seeded.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))["marked_probability"][str(r)]


st.set_page_config(page_title="qfim-bench", layout="wide")
st.title("qfim-bench: Grover-based Quantum Frequent Itemset Mining")
st.caption(
    "Reproducible benchmarking of the companion paper's Grover-based QFIM circuit. "
    "Simulator panels run live; the hardware panel shows archived ibm_marrakesh results "
    "and never re-runs them."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["1. Theory vs. simulator", "2. Start-state comparison", "3. Hardware results (archived)", "4. Classical baselines"]
)

# ---------------------------------------------------------------------------
# Panel 1: theoretical Eq. (4) curve vs. the noiseless simulator, uniform start
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("Eq. (4): theoretical vs. noiseless-simulator success probability")
    col1, col2, col3 = st.columns(3)
    n_items = col1.slider("n_items", 2, 8, 5)
    threshold = col2.slider("oracle threshold t", 0, n_items, 2)
    max_r = col3.slider("max Grover iterations r", 1, 6, 4)

    rows = []
    theta = None
    M = N = None
    for r in range(1, max_r + 1):
        theo, emp = noiseless_p(n_items, threshold, r, "uniform")
        rows.append({"r": r, "theoretical_p": theo, "empirical_p (noiseless sim)": emp})
    _, info = build_grover_circuit(n_items, threshold, 1, initial_state="uniform", seed=42)

    df1 = pd.DataFrame(rows).set_index("r")
    st.line_chart(df1)
    st.dataframe(df1.style.format("{:.4f}"))
    st.caption(
        f"M={info.M}, N={info.N}, theta={info.theta:.4f} for this configuration. "
        "The uniform start reproduces Eq. (4) within sampling noise: qfim-bench's default, "
        "simulator-verified behaviour."
    )

# ---------------------------------------------------------------------------
# Panel 2: uniform vs. ansatz start state, noiseless
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Start-state choice changes the noiseless curve entirely")
    st.caption(
        "Eq. (4) assumes a uniform start. The companion paper's hardware circuits used a random "
        "EfficientSU2 ansatz start instead. This panel shows the difference with no hardware noise."
    )
    rows2 = []
    for r in range(1, 5):
        for init in ["uniform", "ansatz"]:
            theo, emp = noiseless_p(5, 2, r, init)
            rows2.append({"r": r, "start": init, "noiseless empirical p": emp, "theory (Eq.4)": theo})

    df2 = pd.DataFrame(rows2)
    pivot = df2.pivot(index="r", columns="start", values="noiseless empirical p")
    pivot["theory (Eq.4)"] = df2.groupby("r")["theory (Eq.4)"].first()
    st.line_chart(pivot)
    st.dataframe(pivot.style.format("{:.4f}"))
    st.caption(
        "The ansatz start is flat near 0.80 at every r, with no noise applied. The flatness is a "
        "property of the start state, not of hardware noise. Use initial_state='uniform' to "
        "reproduce the oscillating theoretical curve."
    )

# ---------------------------------------------------------------------------
# Panel 3: archived hardware results (uniform start, ibm_marrakesh), static
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("Real hardware results: uniform start, ibm_marrakesh (archived)")
    st.caption(
        "Five jobs submitted once under a write-once prediction manifest "
        "(campaigns/uniform_marrakesh/manifest.json). Measured values are read from the saved counts. "
        "The noisy-simulator column is precomputed with examples/precompute_noisy_sim.py (seed 42). "
        "This panel never contacts IBM Quantum."
    )

    labels = [("r=1", "r1"), ("r=2", "r2"), ("r=2 (repeat)", "r2_repeat"), ("r=3", "r3"), ("r=4", "r4")]
    rows3 = []
    missing = []
    for label, fname in labels:
        f = CAMPAIGN_DIR / f"{fname}.json"
        if not f.exists():
            missing.append(label)
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        total = sum(d["counts"].values())
        measured = sum(c for b, c in d["counts"].items() if b.count("1") >= 2) / total
        rows3.append({
            "label": label,
            "theory (Eq.4)": d["theoretical_p"],
            "measured (hardware)": measured,
            "noisy sim (FakeMarrakesh)": noisy_p(d["r"]),
        })

    if rows3:
        df3 = pd.DataFrame(rows3).set_index("label")
        st.bar_chart(df3[["theory (Eq.4)", "measured (hardware)", "noisy sim (FakeMarrakesh)"]])
        st.dataframe(df3.style.format({
            "theory (Eq.4)": "{:.5f}",
            "measured (hardware)": "{:.4f}",
            "noisy sim (FakeMarrakesh)": "{:.4f}",
        }))
        st.caption(
            "Hardware sits flat near 0.80, well below Eq. (4)'s predicted peak at r=3, and close to "
            "the uniform-distribution reference 26/32 = 0.8125. The noisy simulator stays within about "
            "0.012 of the hardware value at each r for this start state."
        )
    if missing:
        st.info(f"No archived data found for: {', '.join(missing)} (expected in campaigns/uniform_marrakesh/)")

# ---------------------------------------------------------------------------
# Panel 4: classical baseline comparison
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("Classical frequent-itemset mining baselines")
    k = st.slider("top_k_items", 3, 8, 5)
    min_support = st.slider("min_support", 0.01, 0.5, 0.05, step=0.01)

    if not SAMPLE_DATA.exists():
        st.warning(f"Sample dataset not found at {SAMPLE_DATA}")
    else:
        transactions = load_transactions(str(SAMPLE_DATA))
        order = select_top_k_items(transactions, k)
        reduced = reduce_to_selected_items(transactions, order)
        truth = set(brute_force_frequent_itemsets(reduced, min_support))
        baseline = run_classical_baseline(reduced, min_support)

        rows4 = []
        for name, result in baseline.items():
            rows4.append({
                "algorithm": name,
                "itemsets found": len(result.frequent_itemsets),
                "matches brute force": set(result.frequent_itemsets) == truth,
                "runtime (s)": result.runtime_seconds,
                "peak memory (KB)": result.peak_memory_bytes / 1024,
                "note": result.algorithm_note or "-",
            })
        st.dataframe(pd.DataFrame(rows4).set_index("algorithm"))
        st.caption(f"Ground-truth frequent itemsets (brute force): {len(truth)}. Items: {order}")

st.divider()
st.caption(
    "qfim-bench, Apache-2.0. This dashboard is a demo. The software is used programmatically, "
    "as described in the README."
)
