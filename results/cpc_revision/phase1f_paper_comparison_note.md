## Phase 1F vs the paper's quoted medians (0.016-0.024 / 0.42-0.78)

`phase1f_diffusion_pitfall.csv` already reports median + IQR (q1/q3) per (M, r), for both
`ansatz_matched` and `ansatz_hadamard`, from the 30 noiseless seeds in
`results/sim/start_state_design.json["noiseless"]` (`results/sim/start_state_design.json["noiseless_seeds"] == 30`).

The paper's 0.016-0.024 / 0.42-0.78 range is **not** the range of per-r medians — it is
`start_state_design.json["flat_table_noiseless"]`'s `median_range` field: for each M, the script
(`analysis/start_state_design.py`, `FLAT_RANGE = 0.10`) takes `max(median over r) - min(median over r)`
on the median curve, i.e. a flatness statistic, not a value.

| start | M=1 | M=2 | M=3 | M=4 | quoted in CLAIMS_MAP.md |
|---|---|---|---|---|---|
| ansatz_hadamard median_range | 0.01578 | 0.01716 | 0.02404 | 0.01813 | 0.016-0.024 |
| ansatz_matched median_range | 0.41675 | 0.77869 | 0.65887 | 0.70796 | 0.42-0.78 |

Both match the paper's quoted range to 2-3 significant figures (`flat_table_noiseless` entries
above, from `results/sim/start_state_design.json`). No discrepancy -- the only gap was in how the
comparison was framed (raw per-r medians vs. the flatness statistic the paper actually reports),
not in the underlying numbers. `flat=True` for every `ansatz_hadamard` row (range < 0.10) and
`flat=False` for every `ansatz_matched` row, confirming B1 (CLAIMS_MAP.md): Hadamard diffusion
gives a flat curve, matched diffusion does not.
