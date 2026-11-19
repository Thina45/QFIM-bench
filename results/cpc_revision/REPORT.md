# CPC revision report

All numbers below cite the file they come from. Nothing in this report was estimated or
recalled from memory; every figure is read from a saved JSON/CSV in `results/cpc_revision/`
or `results/hardware/`. Run 3 (replication, day B) has **not** been submitted; it waits for a
separate "go" at least 12 hours after Run 1's completion.

## 0. Phase 0 — inventory (full detail in the session transcript; key facts restated here)

- `campaigns/ladder_v2` (Tier A, n=3) and `campaigns/ladder_v2b` (Tiers B/C, n=4/5): the "5 days"
  per tier were two back-to-back same-day sessions on 2026-10-08, not five calendar days. Tier A
  shares one calibration timestamp; Tier B + Tier C runs 1-3 share a second; Tier C runs 4-5 used a
  third, ~19 minutes later. Transpiled circuits are identical across all 5 runs within each tier.
- No T1/T2/gate/readout errors were saved in the original manifests, only `calibration_timestamp`;
  exact historical snapshots were retrieved read-only this session
  (`results/cpc_revision/historical_calibration.json`).
- `uniform_marrakesh`: separate v1 campaign (n=5, M=26/32 degenerate regime, 2026-10-06).

## 1. Original-campaign billing re-verification (user check 1)

Source: `results/cpc_revision/original_campaigns_billing_verification.json`, built from
`job.metrics()` on every stored job ID (read-only).

| Campaign | Jobs | True billed s | Matches manifest? |
|---|---|---|---|
| ladder_v2 | 6 | 104.0 | yes, exact |
| ladder_v2b | 10 | 225.0 | yes, exact |
| **combined** | **16** | **329.0** | **matches the paper's "329 s across 16 jobs" exactly** |
| uniform_marrakesh | 5 | 68.0 | separate campaign, correctly not part of the 329 s/16-job figure |

No undercounting in the original campaigns. The billing bug found later in this session (below)
affected only the new CPC-revision jobs.

## 2. Classical-baseline q=0 bug (user check 2)

Source: `src/qfim_bench/search_cost.py` (fix), `results/cpc_revision/phase1a_classical_baseline.csv`
(corrected output). Exactly 3 rows changed, nothing else:

| Row | Field | Old | New |
|---|---|---|---|
| A (n=3), r=0 | classical_Pc | 0.0 | 0.125 |
| A (n=3), r=0 | better_than_classical | True | False |
| B (n=4), r=0 | classical_Pc | 0.0 | 0.125 |
| B (n=4), r=0 | better_than_classical | True | False |
| C (n=5), r=0 | classical_Pc | 0.0 | 0.125 |
| C (n=5), r=0 | better_than_classical | True | False |

Corrected reading of `phase1a_classical_baseline.csv`: hardware beats the classical query baseline
at r=1 and r=2 for n=3 and n=4; for n=5, only at r=1 (lower CI 0.2594 > P_c 0.2379), not at r=2
(0.1892 < 0.3395). r=0 is a tie by construction (both equal M/N) in every tier, not a win.

## 3. Phase 1F statistic clarification (user check 3)

Source: `results/cpc_revision/phase1f_paper_comparison_note.md`. The paper's quoted 0.016-0.024 /
0.42-0.78 is the **median_range** statistic (`max(median over r) - min(median over r)` per M, from
`results/sim/start_state_design.json["flat_table_noiseless"]`), not the raw per-r median values.

| Diffusion | M=1 | M=2 | M=3 | M=4 | Paper range |
|---|---|---|---|---|---|
| Hadamard median_range | 0.01578 | 0.01716 | 0.02404 | 0.01813 | 0.016-0.024 |
| Matched median_range | 0.41675 | 0.77869 | 0.65887 | 0.70796 | 0.42-0.78 |

Both match to 2-3 significant figures. No real discrepancy — recommend the manuscript name this
statistic explicitly (`median_range`) so it isn't confused with a per-r median value.

## 4. Phase 1 A-F (existing data, read-only) — summary

Full tables in `phase1a_classical_baseline.csv`, `phase1b_global_fit.json` + `phase1b_residuals.csv`,
`phase1c_echo_vs_grover_fit.csv` (EXPLORATORY), `phase1d_distances.csv`, `phase1e_digital_twin.json`,
`phase1f_diffusion_pitfall.csv`, `phase1_exploratory_tierC_calibration_split.csv` (EXPLORATORY).

- **1A**: see section 2 above (corrected).
- **1B**: per-size f = 0.99416 (n=3), 0.99402 (n=4), 0.99542 (n=5); global f = 0.99443. Peak
  locations match exactly (r=2 at n=3, r=1 at n=4/5). Reduced chi-square per `phase1b_residuals.csv`:
  A=108.4, B=83.8, C=55.3, global=96.2 (all >>1 — binomial shot noise alone does not explain the
  dispersion; real variance includes calibration drift the model does not capture).
- **1C (EXPLORATORY)**: echo-derived f tracks the Grover-fit f within ~0.001 at all three sizes,
  both below the simulator's 0.9967.
- **1D**: farthest-from-ideal cells are Tier A r=3/r=4 and Tier C's high-depth cells.
- **1E**: digital twin built from the exact 2026-10-08 calibration (qiskit-aer's
  `NoiseModel.from_backend_properties`, `thermal_relaxation=False` — this device's properties have
  no `frequency` field, so the T1/T2 term could not be included; stated as a caveat). The twin's TVD
  is smaller than generic FakeMarrakesh's at all 15 ladder cells.
- **1F**: Hadamard (mismatched) diffusion collapses to ~0.01-0.17 regardless of r; matched diffusion
  reaches up to 0.86. See section 3 for the paper-comparison statistic.
- **Tier C calibration split (EXPLORATORY)**: only 2 of 8 cells (`ladder_n5_M4_r3`,
  `readout_n5_ones`) show a difference between runs 1-3 and runs 4-5 exceeding within-subgroup
  spread; n=2/3 per subgroup is too small for a reliable interval.

## 5. New hardware runs — projected vs true billed seconds

Source: `results/cpc_revision/billing_correction.json` (true values, from `job.metrics()`, not the
manifest's `usage_seconds` — see the bug below).

| Run | Device | Jobs | Projected s | True billed s |
|---|---|---|---|---|
| 1 (replication) | ibm_marrakesh | 15 | 325.0 | 325.0 (exact) |
| 2 (DD-off ablation) | ibm_marrakesh | 5 | 105.0 | 100.0 |
| 4 (second device) | ibm_kingston | 15 | 325.0 (assumed) | 315.0 (assumption held) |
| **Total** | | **35** | **755.0** | **740.0** |

740.0 s against the 1,200 s hard cap — 460 s of headroom remaining before Run 3.

**Billing bug found and fixed**: 4 of the 35 jobs had `usage_seconds` recorded as `0.0` in their
campaign manifest. `HardwareBackend._billed_seconds()` read `job.usage()`, which returned `0`
(not an exception) immediately after `job.result()`, before the runtime finalized billing. Every
affected job's true value, read via `job.metrics()`, was correct and nonzero. Fixed in
`src/qfim_bench/backends.py` to prefer `metrics()` first; regression test added
(`tests/test_hardware_batch.py::test_metrics_quantum_seconds_is_preferred_over_a_stale_zero_from_usage`).
All 35 jobs' recorded-vs-true values are in `billing_correction.json`.

## 6. Run 1 vs the 2026-10-08 data (H1 evidence)

Source: `results/cpc_revision/new_vs_oct8.json`.

- **n=3, r=2** (the cell H1 was pre-stated for): Oct 8 mean 0.7959 (t-CI half-width 0.0068) vs
  Run 1 mean 0.8199. |diff| = 0.024 > 0.0068 — **exceeds the within-sitting CI**.
- Across all 15 ladder cells, 13 of 15 show a difference exceeding their original within-sitting CI
  (only the two r=0 baselines stayed inside). Direction is tier-dependent (Tier A mostly higher,
  Tier B mostly lower on 2026-11-19 than on 2026-10-08), consistent with ordinary calibration drift
  over ~6 weeks rather than a systematic error.

## 7. Run 2 (DD off) vs Run 1 Tier B (DD on), n=4 (H2 evidence)

Source: `results/cpc_revision/cpc_runs_analysis.json`.

| r | DD on (Run 1 Tier B) | DD off (Run 2) | diff (on - off) | 95% CI of diff | Reading |
|---|---|---|---|---|---|
| 0 | 0.1242 | 0.1267 | -0.0025 | [-0.0063, 0.0014] | inconclusive |
| 1 | 0.5673 | 0.6425 | **-0.0751** | **[-0.1107, -0.0396]** | **DD hurts, significant** |
| 2 | 0.5161 | 0.5433 | -0.0272 | [-0.0571, 0.0027] | inconclusive |
| 3 | 0.2022 | 0.1604 | 0.0418 | [0.0159, 0.0677] | DD helps, significant |
| 4 | 0.1371 | 0.1441 | -0.0070 | [-0.0169, 0.0030] | inconclusive |

## 8. Run 4 (ibm_kingston) vs Run 1 (ibm_marrakesh)

Source: `results/cpc_revision/cpc_runs_analysis.json`. Kingston outperforms marrakesh at every
checked cell (e.g. `ladder_n4_M2_r2` +0.167, `ladder_n5_M4_r1` +0.124, `echo_n4_M2_r2` +0.220),
consistent with its lower median two-qubit gate error measured in this session's device survey
(0.00192 vs marrakesh's 0.00293).

## 9. H1 / H2 / H3 — stated plainly

**Correction (caught on review): H1 as actually written compares Run 1 to Run 3, not Run 1 to the
2026-10-08 data.** Quoting `review/OPERATING_POINT_ADDENDUM_V3.md` verbatim: "H1. Day-to-day
variation of the r=2 (n=3) success probability (|Run 1 mean − Run 3 mean|) is larger than the
within-sitting CI width from Run 1's own 5 daily values." Run 3 has not been submitted, so **H1 is
PENDING, not supported** — the earlier draft of this report wrongly evaluated it against the Oct-8
data (a ~6-week gap) and called it "supported"; that was a different, exploratory comparison
(long-term drift), not H1. Section 6's Run-1-vs-Oct-8 finding is retained below as exploratory
long-term drift, not as an H1 result.

- **H1 (|Run 1 mean − Run 3 mean| at n=3, r=2, > Run 1's own within-sitting CI width): PENDING.**
  Cannot be evaluated until Run 3 exists.
- **H2** (verbatim): "DD improves n=4 hardware success at r=1 and r=2: Run 1 Tier B (DD on) mean
  exceeds Run 2 (DD off) mean, with the lower CI of the difference above 0." **NOT SUPPORTED.**
  r=1 is significant in the *opposite* direction (DD off outperforms DD on); r=2 is inconclusive.
  One contradicting result is enough to call this not supported, not "partially" supported.
- **H3: there is no H3 in the committed V3 addendum.** `review/OPERATING_POINT_ADDENDUM_V3.md`
  states only H1 and H2 (grep-confirmed). An H3 exists only in the earlier, separate
  `review/OPERATING_POINT_ADDENDUM.md`: "H3 (n=5): the rules are not met" — about the n=5
  operating-point criterion, not about device ordering by median two-qubit error. The earlier
  draft of this report used that definition without flagging that it isn't part of V3's own
  hypothesis list; flagged explicitly here. No hypothesis about device ordering by two-qubit error
  has been preregistered anywhere; section 8's kingston-vs-marrakesh comparison and Phase 1's/this
  session's fit-vs-2Q-error figure (`fig_i`) are exploratory findings, not a hypothesis test.
  Re-evaluating the original addendum's H3 on Run 1's fresh n=5 data with the same
  `criterion_rules_hardware` logic reused from `results/hardware/ladder_v2b/analysis.json`: ratio
  1.76 (<3), floor 0.22 (<0.40), gap 0.095 (<0.20) — all rules still fail. **SUPPORTED** (under that
  original definition only), same
  conclusion as the original Oct 8 data.

## 9b. Preregistration timing (user check: committed/pushed before the first submission?)

Commit `494632b` (message: "Preregister CPC-revision hardware addendum V3 (Runs 1-4) before any
new data") contains `review/OPERATING_POINT_ADDENDUM_V3.md` and the four draft manifests. Its
commit timestamp (author = committer, both local and on the GitHub commit object) is
**2026-11-19 14:46:33 +05:30** (`2026-11-19T09:16:33Z`). `git push -u origin cpc-revision`
completed successfully (confirmed by its own success output: "new branch cpc-revision ->
cpc-revision") in the same turn, immediately after that commit and strictly before the adoption
script, dry-runs, or any job submission were executed. The first Run 1 job (`A_run1`,
`dbvbvf782tmc73dup1c0`) was created at **2026-11-19 14:52:04.949 +05:30** — about 5.5 minutes after
the commit. **The addendum was committed (and, by tool-call ordering, pushed) before the first
submission.** Caveat: GitHub's public events API returned an empty list for this repository (it
appears to be private, and no authenticated query was attempted), so there is no independent
GitHub-side "push received" timestamp beyond the commit's own timestamp and the ordering of tool
calls in this session; no timestamp has been backdated or inferred beyond what's stated here.

## 9c. Run 1 and Run 4, separately (classical baseline, criterion, fit) — no data changed

Sources: `results/cpc_revision/cpc_run{1,4}_classical_baseline.csv`, `cpc_run{1,4}_criterion.json`,
`cpc_run{1,4}_fit.json`, `cpc_run{1,4}_fit_residuals.csv`, `run1_run4_median_2q_error.json`.

**Deviation found while building this**: the addendum said Run 1 would reuse "the SAME physical
qubit layout the transpiler chose for ladder_v2/v2b," but `analysis/run_cpc_runs.py` re-transpiled
fresh against live calibration instead of reusing the original transpiled circuit objects. Actual
Run 1 layouts (e.g. `(53,54,55)` for the n=3 circuits) do not match the Oct-8 layout `(5,6,7)`.
This is a real deviation from the preregistered plan, not a data error — flagged here rather than
silently absorbed into the numbers below.

- **Classical baseline**: Run 1 — 4 of 15 ladder cells beat classical; Run 4 — 5 of 15.
- **Operating-point criterion** (`criterion_rules_hardware`, reused unchanged):

  | Tier | Run 1 (marrakesh) | Run 4 (kingston) |
  |---|---|---|
  | A (n=3) | PASS (ratio 6.54) | PASS (ratio 6.78) |
  | B (n=4) | FAIL — rule 3 only | **PASS** (ratio 5.43, all 4 rules) |
  | C (n=5) | FAIL (ratio 1.76) | FAIL (ratio 2.66, closer but still fails) |

  Run 4/kingston passes Tier B where the Oct-8 data, Run 1, and the original addendum's prediction
  all failed it — a new result, not previously seen in this project.
- **Global depolarizing fit f**: Run 1 (marrakesh) f=0.99371, CI [0.99364, 0.99378]; Run 4
  (kingston) f=0.99645, CI [0.99642, 0.99650]. For reference, the original Oct-8 global fit was
  f=0.99443 (`phase1b_global_fit.json`).
- **Median two-qubit gate error**, computed from the exact calibration snapshot at each run's own
  recorded `calibration_timestamp`, restricted to the physical qubit pairs the ladder circuits
  actually used (not a generic device-wide figure): Oct-8 marrakesh 0.00180, Run 1 marrakesh
  0.00186, Run 4 kingston 0.00133. Higher error tracks lower fit f at all three points — Fig I.

## 10. Figures

- `figures/cpc/fig_a.{pdf,png}`, `fig_b.{pdf,png}`: regenerated with the corrected Phase 1A data.
  Fig A intentionally does **not** add Run 1/Run 4 as extra series (would overcrowd the existing
  three-panel ideal/FakeMarrakesh/hardware layout) — that comparison is in the new Figs F/G instead.
- `figures/cpc/fig_f.{py,pdf,png}` (new): day-to-day drift, r=2 success per day per n, from section 6.
- `figures/cpc/fig_g.{py,pdf,png}` (new): DD on vs off at n=4 vs r, from section 7.
- `figures/cpc/fig_i.{py,pdf,png}` (new): fitted global f vs. median two-qubit error, one point per
  device/session (Oct-8 marrakesh, Run 1 marrakesh, Run 4 kingston), from section 9c.
- Figs C, D, E, H: unchanged from the earlier Phase 1 pass.

## 11. Tests

198 passed, 0 failed (184 original + 11 from the Phase 1 pass + 2 regression tests for DD-enable
and the billing fix + 1 other), confirmed after the billing-bug fix.

## 12. What was not done / deviated

- Run 3 was explicitly not submitted — waits for a separate "go" ≥12 h after Run 1's completion.
- `qBraid` was surveyed (`results/cpc_revision/qbraid_survey.json`) and recommended against for
  Run 4 (no quotable IBM pricing, no fixed-price alternative fits the budget/shot-count floor).
- Nothing under `campaigns/ladder_v2(/b)`, `results/hardware/ladder_v2(/b)`, or existing `review/`
  files was modified.
- Nothing in this round was committed to git; all new/changed files remain uncommitted on the
  `cpc-revision` branch pending your review.
