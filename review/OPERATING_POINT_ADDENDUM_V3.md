# Addendum V3 — CPC revision hardware campaign (not adopted, nothing submitted)

This addendum extends `review/OPERATING_POINT_ADDENDUM.md` (unchanged, not edited here) for the
Computer Physics Communications revision. It describes four proposed runs. **No job has been
submitted under this addendum.** Draft manifests (predictions written before any data, as the
earlier campaigns did) are in `review/preregistration/cpc_run{1,2,3,4}_manifest_DRAFT.json`.

## What is unchanged from campaigns/ladder_v2 + ladder_v2b

(n, M) = (3,1), (4,2), (5,4), M/N = 1/8 throughout, oracle style `mcz`, uniform start, matched
diffusion, r = 0..4, echo control at r_opt, readout-zeros/readout-ones controls, 8192 shots,
optimization_level=3, seed_transpiler=42, dynamical decoupling XpXm (except Run 2).

## Honest description of what was actually run before (Phase 0 finding, stated here because it
bears on how "replication" and "day" are used below)

`ladder_v2`'s five "tierA_day1..5" jobs and `ladder_v2b`'s Tier B/C runs were **not** run on five
different calendar days. All were submitted back-to-back in two sessions on 2026-10-08 (Tier A:
12:49-12:58 UTC; Tier B and Tier C runs 1-3: 13:04-13:11 UTC; Tier C runs 4-5: 13:11-13:12 UTC).
Tier A shares one calibration timestamp; Tier B and Tier C runs 1-3 share a second; Tier C runs 4-5
used a third, about 19 minutes later. Transpiled circuits (depth, two-qubit count, physical layout)
are identical across the five runs within each tier regardless of the calibration shift. This is
why Run 3 below requires a real ≥12-hour gap: Runs 1 and 2 (and the existing campaigns) do not
contain genuine day-to-day replication, so H1 cannot be tested without it.

## Runs proposed

- **Run 1 (replication, day A).** Full ladder (all three tiers), ibm_marrakesh, 5 repeats/tier, DD
  on. 15 jobs. Manifest: `cpc_run1_manifest_DRAFT.json`.
- **Run 2 (DD-off ablation, day A).** n=4 only, otherwise identical to Run 1's Tier B, DD off. 5
  jobs. Manifest: `cpc_run2_manifest_DRAFT.json`.
- **Run 3 (replication, day B, ≥12 h after Run 1 completes).** Full ladder, ibm_marrakesh, 3
  repeats/tier, DD on. 9 jobs. Manifest: `cpc_run3_manifest_DRAFT.json`.
- **Run 4 (second device).** Full ladder, **ibm_kingston**, 5 repeats/tier, DD on. 15 jobs.
  Manifest: `cpc_run4_manifest_DRAFT.json`. Candidate chosen from a read-only device survey this
  session (no circuits run): `ibm_kingston` (0 pending jobs, median two-qubit gate error 0.00192 at
  query time) over `ibm_fez` (0 pending jobs, 0.00253); both Heron r2, same family as
  `ibm_marrakesh` (4 pending jobs, 0.00293). `ibm_fez` is dropped per the user's decision.

## Predictions, written before any new data

Each run's draft manifest carries two sets, both already-existing-data derived (no number here is
guessed): the original FakeMarrakesh predictions from `campaigns/ladder_v2(/b)` (unchanged), and a
second set from the Phase 1B depolarizing fit to the EXISTING hardware data
(`results/cpc_revision/phase1b_global_fit.json`, `results/cpc_revision/phase2_fit_predictions.csv`):
per-tier f = 0.99416 (n=3), 0.99402 (n=4), 0.99542 (n=5); global f = 0.99443. The fit reproduces the
known peak locations (r=2 at n=3, r=1 at n=4 and n=5) exactly on the existing data (Phase 1B), which
is why it is used as a second prediction here rather than only FakeMarrakesh. Tolerance band:
half-width = 5·sqrt(p(1-p)/8192) + 0.05, unchanged convention, scored against the FakeMarrakesh
prediction as before (the fit prediction is reported alongside, not substituted as the primary
criterion, since it was fit to the very data it would be "predicting").

## Hypotheses, stated before data

- **H1.** Day-to-day variation of the r=2 (n=3) success probability (|Run 1 mean − Run 3 mean|) is
  larger than the within-sitting CI width from Run 1's own 5 daily values.
- **H2.** DD improves n=4 hardware success at r=1 and r=2: Run 1 Tier B (DD on) mean exceeds Run 2
  (DD off) mean, with the lower CI of the difference above 0.

Neither is assumed true. A miss on either is reported as such, not revised after the fact.

## Budget — hard cap 1,200 quantum-seconds for ALL new runs combined

Enforced by `usage_budget_seconds` in each draft manifest (existing `HardwareBackend.run_batch`
mechanism — refuses to submit once cumulative billed seconds in that manifest reach the budget).
Projections are built from this session's real, already-billed per-job seconds (read via
`QiskitRuntimeService.job(...).metrics()`), not estimated from memory:

| Run | Backend | Jobs | Basis | Projected s | Budget allocated |
|---|---|---|---|---|---|
| 1 | ibm_marrakesh | 15 (5×3 tiers) | A:20.0s, B:21.0s, C:24.0s per job (measured, Oct 8 campaign) | 325.0 | 350 |
| 2 | ibm_marrakesh | 5 | Tier B rate, DD off assumed not to change execution time | 105.0 | 120 |
| 3 | ibm_marrakesh | 9 (3×3 tiers) | same per-job rates, 3 reps | 195.0 | 220 |
| 4 | ibm_kingston | 15 (5×3 tiers) | **assumed** equal to marrakesh's rates — untested device, flagged | 325.0 | 350 |
| **Total** | | **44** | | **950.0** | **1040** |

950 s projected (1040 s allocated with margin) against the 1,200 s cap — **under the 1,100 s
threshold, so no cuts are proposed.** Run 4's projection is the least certain entry (new device,
no prior billed-time data for this project); its real billed time will be recorded and could push
the running total higher if it diverges, which is why its allocated budget (350s) already carries a
25s margin over the naive 325s estimate, and why it is enforced per-manifest independently of the
other three runs.

## Per-job recording requirement

Every new job's manifest entry will save the calibration timestamp (already project convention)
**and**, newly, the live `backend.properties()` snapshot at submission (T1, T2, readout_error,
gate_error for the qubits used) — demonstrated feasible this session via read-only
`backend.properties(datetime=...)` calls (see `results/cpc_revision/historical_calibration.json`).
This closes the Phase 0 gap where the original campaigns recorded only a timestamp, not the
underlying error rates.

## What this does not decide

Nothing is adopted or submitted. The user chooses Run 4's device (kingston vs fez — fez is listed
above only as the rejected alternative) and gives the explicit "go" for Runs 1+2 before anything is
submitted; Run 3 requires a second, later "go" (it must follow Run 1 by ≥12 hours); Run 4 can be
batched with Runs 1+2 approval or held separately, the user's choice.
