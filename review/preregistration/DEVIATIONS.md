# Deviations from the adopted preregistration

Written and committed BEFORE any hardware job is submitted. Manifest: `campaigns/ladder_v2/manifest.json`,
sha256 `6dcfc075d5e4af26a786ca2ee2cc911955f0104e6fb228da5c51bdd783bef3b9`.

## D1. Tier A repeats run in one sitting, not one per day (user instruction, 2026-10-08)

Preregistered: one Tier A job per day for 5 days. Actual: the 5 Tier A jobs are run one after another
in the same sitting, at the user's explicit request to finish quickly.

What this changes:
- The 5 repeats share one calibration period, so day-to-day drift is not sampled. The t-interval across
  the 5 repeats (the preregistered primary uncertainty) will therefore be narrower than a 5-day interval
  would have been and must not be read as including drift.
- The randomised circuit order is kept: each job uses its own preregistered schedule (`day_1` ... `day_5`).
- Everything else (circuits, predictions, tolerance bands, caps, shots) is unchanged.

## D2. Tag not created

The checklist asked for the git tag `prereg-ladder-v2` before the probe. The user pushed `main` only
(including the adoption commit ec08f12); no tag exists. The adoption commit's GitHub timestamp is the
only public timestamp of the plan. The write-up must not call the plan "tagged".

## D3. CI waived

CI #1 was green on b1f3988; CI #2 on 4acc9d3 was not awaited (user instruction, recorded in the manifest).

## D4. Code added after adoption

After the adoption commit, `HardwareBackend.run_batch` gained per-job metadata recording (calibration
timestamp, physical qubits, depth, two-qubit count) and `analysis/run_ladder_campaign.py` was added. Neither
changes the manifest, circuits, predictions or limits.
