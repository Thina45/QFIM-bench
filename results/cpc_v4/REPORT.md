# CPC v4 report

**No hardware job was submitted for any part of this pass.** Everything below is read-only use of
already-saved campaign/manifest/results files, saved calibration snapshots retrieved read-only via
`backend.properties(datetime=...)`, and local simulation (`qiskit-aer`). New outputs are under
`results/cpc_v4/` and `figures/cpc/`; no existing data file was modified.

## 1. DD layout check: Run 1 vs Run 2 (Tier B, n=4)

Source: `campaigns/cpc_run1/manifest.json`, `campaigns/cpc_run2/manifest.json` (`circuits_info`).

| Circuit | Run 1 layouts used (across 5 repeats) | Run 2 layout (all 5 repeats) | Two-qubit gates (both runs) |
|---|---|---|---|
| `ladder_n4_M2_r0` | (10,97,139,140) x3, (5,10,14,153) x2 | (5,10,14,153) | 0 |
| `ladder_n4_M2_r1` | (137,146,147,148) x3, (2,3,4,16) x2 | (2,3,4,16) | 56 |
| `ladder_n4_M2_r2` | (137,146,147,148) x3, (2,3,4,16) x2 | (2,3,4,16) | 113 |
| `ladder_n4_M2_r3` | (137,146,147,148) x3, (2,3,4,16) x2 | (2,3,4,16) | 170 |
| `ladder_n4_M2_r4` | (137,146,147,148) x3, (2,3,4,16) x2 | (2,3,4,16) | 227 |
| `echo_n4_M2_r2` | (137,146,147,148) x3, (2,3,4,16) x2 | (2,3,4,16) | 227 |
| `readout_n4_zeros/ones` | (10,97,139,140) x3, (5,10,14,153) x2 | (5,10,14,153) | 0 |

**Layouts were NOT identical.** Run 1 itself used two distinct physical-qubit layouts across its
own 5 repeats (3/5 on one, 2/5 on the other — the same live-calibration-dependent transpiler
behaviour documented for Run 3 in `results/cpc_revision/REPORT.md` section 13). Run 2 used only
the SECOND of those two layouts, for all 5 repeats. So Run 1 and Run 2 match exactly for 2 of
Run 1's 5 repeats (runs 2 and 5), and differ in physical qubits for the other 3 (runs 1, 3, 4).
**Two-qubit gate counts are identical across both layouts for every circuit** (56/113/170/227,
exactly, no gate-count confound), so H2 (section 7/9 of `results/cpc_revision/REPORT.md`) is
layout-partially-confounded but NOT gate-count-confounded. Depths differ by ~1% between the two
layouts (e.g. r=1: 213 vs 216), the same small, previously-documented effect.

## 2. Drift without confound: Run 1 vs Run 3 (r=1, r=2; n=4, n=5)

Source: `results/cpc_revision/cpc_runs_analysis.json` (means, t-CIs); Welch's t-test
(`scipy.stats.ttest_ind(equal_var=False)`) on the 5 vs 3 per-repeat values; depolarizing-model
prediction uses each run's own per-size fit and `theoretical_success_probability`.

| n | r | Run 1 mean [95% CI] | Run 3 mean [95% CI] | diff | Welch t | Welch p | Gate counts (R1→R3) | Predicted effect of gate-count diff |
|---|---|---|---|---|---|---|---|---|
| 4 | 1 | 0.5673 [0.5263, 0.6084] | 0.5054 [0.4938, 0.5170] | −0.0620 | 4.123 | 0.0128 | 56→56 (gate-matched) | 0 (no confound possible) |
| 4 | 2 | 0.5161 [0.4912, 0.5411] | 0.4348 [0.3891, 0.4805] | −0.0813 | 5.841 | 0.0026 | 113→113 (gate-matched) | 0 (no confound possible) |
| 5 | 1 | 0.2203 [0.2103, 0.2303] | 0.2082 [0.2047, 0.2117] | −0.0121 | 3.282 | 0.0265 | 329→330 (+1) | −0.00053 (negligible vs. observed −0.0121) |
| 5 | 2 | 0.1686 [0.1652, 0.1719] | 0.1331 [0.1257, 0.1406] | −0.0354 | 16.802 | 0.0001 | 668→669 (+1) | −0.00009 (negligible vs. observed −0.0354) |

**All four cells show a significant Run 1 → Run 3 drop (Welch p < 0.03 in every case) that is NOT
explained by a gate-count confound**: n=4 is exactly gate-matched at both r (no confound possible
by construction); n=5's 1-gate difference predicts an effect 20-400x smaller than what was
observed. This is in contrast to the n=3, r=2 case (`results/cpc_revision/REPORT.md` section 13),
where the predicted gate-count effect was LARGER than the observed drop and fully explained it.
**n=4 and n=5 at both r=1 and r=2 are therefore clean, confound-free evidence of day-to-day drift**
between Run 1 (2026-11-19) and Run 3 (2026-11-20), strengthening the supplementary finding already
reported in section 13 (previously shown only for n=4, r=2).

## 3. Effective-error ratio, 4 sessions

Source: `analysis/fit_cpc_run3.py` → `results/cpc_v4/cpc_run3_fit.json` (new Run 3 fit, f=0.99257,
inflated CI [0.99128, 0.99360], reduced chi-square 155.7 — same goodness-of-fit caveat as every
other fit in this project); `analysis/median_2q_error_run3.py` → `results/cpc_v4/
run3_median_2q_error.json` (median two-qubit error 0.00196, 9 edges, exact calibration match
confirmed at calibration_timestamp 2026-11-20 03:39:26 — offset +8 min, same indexing-lag
correction as Run 1/Run 4).

### Global (one f per session)

| Session | f | inflated CI | median 2Q error | ratio (1−f)/err | ratio CI |
|---|---|---|---|---|---|
| Oct-8 | 0.99443 | [0.99387, 0.99511] | 0.00180 | 3.095 | [2.714, 3.405] |
| Run 1 | 0.99371 | [0.99339, 0.99401] | 0.00186 | 3.381 | [3.218, 3.553] |
| Run 3 | 0.99257 | [0.99128, 0.99360] | 0.00196 | **3.797** | [3.270, 4.453] |
| Run 4 | 0.99645 | [0.99589, 0.99718] | 0.00133 | 2.669 | [2.122, 3.094] |

Across all 4 sessions, the effective per-gate error this depolarizing model infers is **2.7-3.8x**
the vendor-calibrated two-qubit error — consistent with the earlier 3-point observation, now with
a 4th point that extends the range upward (Run 3 is the highest ratio of the four). Still reported
as an observation (n=4 points), not a general law.

### Per-size (correlated within a session — same median 2Q error shared across n=3/4/5)

| Session | n=3 ratio | n=4 ratio | n=5 ratio |
|---|---|---|---|
| Oct-8 | 3.242 [2.548, 4.035] | 3.320 [2.872, 3.834] | 2.545 [2.117, 2.924] |
| Run 1 | 2.508 [2.118, 2.835] | 3.880 [3.670, 4.123] | 3.244 [2.713, 3.715] |
| Run 3 | 2.464 [1.958, 2.930] | **4.915** [4.543, 5.272] | 3.247 [3.038, 3.472] |
| Run 4 | 2.466 [1.609, 3.397] | 2.989 [1.679, 4.586] | 2.494 [1.985, 2.967] |

No consistent ordering by n across sessions (n=4 is highest for Run 1/Run 3 but not Oct-8/Run 4);
the per-size CIs for Run 4 are wide (only 5 repeats, one calibration timestamp). Fig I updated with
Run 3 as a 4th point (panel a) and 4th bar (panel b).

## 4. Noise model comparison: 1-parameter (f, p_noise) vs 2-parameter (f, SPAM)

Source: `analysis/two_param_spam_fit.py` → `results/cpc_v4/two_param_spam_fit.json`. Model 1
(the existing fit, 2 FREE parameters f and p_noise, fit by binomial MLE to the ladder r-series) vs
Model 2 (f FREE, 1 parameter; p_noise FIXED at the theoretical floor M/N; the ideal curve scaled by
a SPAM factor R=(1−e_spam)^n, where e_spam is a PLUG-IN estimate from that session's own
`readout_n{n}_zeros/ones` controls — NOT fit to the same r-series likelihood, so it does not count
toward Model 2's k for AIC/BIC). k=2 for Model 1, k=1 for Model 2, both evaluated on the same
pooled (g, k, n) ladder data per session.

| Session | Model | f | reduced χ² | AIC | BIC |
|---|---|---|---|---|---|
| Oct-8 | 1 (f, p_noise) | 0.99443 | 96.2 | 590518.9 | 590520.3 |
| Oct-8 | 2 (f, SPAM) | 0.99509 | 157.9 | 591364.0 | 591364.7 |
| Run 1 | 1 (f, p_noise) | 0.99371 | 92.5 | 578440.9 | 578442.3 |
| Run 1 | 2 (f, SPAM) | 0.99432 | 147.9 | 579208.5 | 579209.2 |
| Run 3 | 1 (f, p_noise) | 0.99257 | 155.7 | 347352.8 | 347354.2 |
| Run 3 | 2 (f, SPAM) | 0.99329 | 162.7 | 347555.0 | 347555.7 |
| Run 4 | 1 (f, p_noise) | 0.99645 | 280.1 | 600006.3 | 600007.8 |
| Run 4 | 2 (f, SPAM) | 0.99703 | 338.6 | 600945.7 | 600946.4 |

**Model 1 (free p_noise) wins decisively on AIC and BIC at every session**, despite having one
more free parameter — the AIC/BIC penalty for that extra parameter (+2, +ln(n_data)≈+2.6) is
dwarfed by the NLL gap (hundreds to thousands) between the two models. **Residual pattern that
remains**: Model 2's reduced chi-square is 1.03-1.65x Model 1's at every session (worst at Oct-8,
1.64x), meaning the independent-per-qubit-readout-flip picture of the noise floor
systematically underestimates it — the real asymptotic floor (what Model 1's free p_noise
captures) is higher than SPAM alone predicts, consistent with additional depolarizing/leakage/
crosstalk contributions beyond simple readout error. Neither model achieves reduced chi-square
near 1 (both are phenomenological, per the existing goodness-of-fit caveat); Model 1 remains the
better-supported of the two. Fig S1 updated with both models' residuals (Oct-8 only, matching the
original figure's scope).

## 5. Digital twins: every saved calibration snapshot

Source: `analysis/digital_twins_v4.py` → `results/cpc_v4/digital_twins_v4.json`. Oct-8's twin
(`results/cpc_revision/phase1e_digital_twin.json`) is reused, not recomputed. Historical-properties
indexing-lag offset confirmed exact by direct query: **ibm_marrakesh +8 min, ibm_kingston +18
min** (different backends, different lag) — every twin below is an EXACT calibration match,
confirmed and printed by the script.

| Session | Device | Calibration timestamp | Exact match | Median TVD (hw vs twin) | Median TVD (hw vs generic fake) |
|---|---|---|---|---|---|
| Oct-8 | ibm_marrakesh | 2026-10-08 (3 windows, per tier) | yes | 0.0414 | 0.0485 |
| Run 1 | ibm_marrakesh | 2026-11-19 14:35:58 / 14:48:07 | yes | 0.0472 | 0.0379 |
| Run 3 | ibm_marrakesh | 2026-11-20 03:39:26 | yes | 0.0409 | 0.0330 |
| Run 4 | ibm_kingston | 2026-11-19 05:36:23 | yes | 0.0395 | N/A (no `FakeKingston` in this qiskit-ibm-runtime version) |

**Unexpected finding, reported plainly rather than smoothed over**: Oct-8 is the ONLY session
where the calibration-exact twin is closer to hardware than the generic FakeMarrakesh snapshot
(0.0414 < 0.0485). For both Run 1 and Run 3, the GENERIC snapshot is closer to hardware than the
twin built from that session's own exact calibration (Run 1: 0.0379 < 0.0472; Run 3: 0.0330 <
0.0409). This reverses the Oct-8-only finding already in `results/cpc_revision/REPORT.md`
("twin's TVD is smaller than generic FakeMarrakesh's at all 15 ladder cells") — that statement is
NOT true of Run 1 or Run 3 and should not be generalized beyond Oct-8 in the manuscript. A
plausible explanation (not confirmed): Run 1/Run 3 used FRESH/pinned transpilation against live
calibration rather than the archived FakeMarrakesh snapshot's topology-matched layout, so some of
the twin-vs-hardware gap may be transpilation-related rather than purely a noise-model fidelity
question; this was not isolated further. Run 4 has no generic-fake point for comparison.

## 6. Non-Grover examples (Layer A generality)

`examples/ghz_ladder.py` (GHZ, n=3-6) and `examples/tfim_trotter.py` (1D TFIM, n=4-6, 1-4 Trotter
steps) both run on `SimulatorBackend` (ideal) and `NoisySimulatorBackend` (ibm_marrakesh
calibration-snapshot noise model), apply `noise_analysis.compare_distributions` (TVD/Hellinger),
`reproducibility.repeated_run_check` (5 seeds) and `fit.fit_fidelity_decay` — the SAME Layer A
tools the Grover ladder campaigns use, demonstrating they are not Grover-specific.

- **GHZ** (`results/cpc_v4/ghz_ladder.json`): success = P(all-zeros or all-ones), ideal = 1.0
  exactly at every n (by construction). Fit f=0.99227, CI [0.866, 0.993] (wide: only 4 points, and
  a constant ideal target poorly constrains p_noise). TVD(ideal, noisy) rises monotonically with n
  (0.014 at n=3 to 0.039 at n=6).
- **TFIM** (`results/cpc_v4/tfim_trotter.json`): return probability P(all-zeros), ideal computed
  from the noiseless statevector of the SAME trotterized circuit (not exact continuous-time
  dynamics). Fit f=0.99612, CI [0.99534, 0.99695]. Reproduces the expected decay-with-depth
  pattern across all 12 (n, steps) points; noisy probability tracks ideal closely at low gate
  count and falls further behind as two-qubit gate count grows (e.g. n=6: ideal 0.786→0.159,
  noisy 0.757→0.148 across 1→4 steps).

New Fig O (two panels) and `tests/test_examples_non_grover.py` (5 tests) added.

## 7. Related-software check (Table 8) — NOT COMPLETED

**Could not locate the manuscript file containing "Table 8."** Searched this repository and the
parent workspace (`qfim-bench/`, `Conference/`, `Software_X_journal/`, `patent/`) for a CPC
manuscript source or table; found only `Conference/resubmission/paper/paper.docx` (a different,
already-resubmitted conference paper, not CPC, and its own tables don't match a related-software
comparison) and `qfim-bench/review/QFIM-bench_SoftwareX_Action_Plan.docx` (an action-item list,
not the manuscript). No CPC manuscript source (`.tex`, `.docx`, or otherwise) was found anywhere
I have access to. I did not fabricate project names, "Not reported" cells, or arXiv references for
a table I cannot see — that would risk citing something inaccurately. **This item needs either the
manuscript's file path or the Table 8 content (the list of related projects and which cells are
currently "Not reported") before it can be done.** Everything else in this report (items 1-6, 8)
was completed independent of this.

## 8. Tests

205 tests pass (200 from the prior CPC-revision pass + 5 new in
`tests/test_examples_non_grover.py`). No source code in `src/qfim_bench/` was changed this pass
(all new logic is in `analysis/`, `examples/`, and `figures/cpc/`).

## What was not done / deviated

- Item 7 (related-software check) not completed — see section 7 above.
- Nothing under `campaigns/`, `results/hardware/`, `results/cpc_revision/`, or `review/` was
  modified; all new outputs are in `results/cpc_v4/` and `figures/cpc/`, as instructed.
- No hardware job was submitted for any part of this pass (hard rule, honored).
