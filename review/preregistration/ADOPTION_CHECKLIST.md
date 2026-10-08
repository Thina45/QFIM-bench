# Adoption checklist for the ladder preregistration

Status: ADOPTED 2026-10-08 (manifest at campaigns/ladder_v2/manifest.json). CI item waived by the user. Tag and probe still pending.
written to `campaigns/`, or submitted until every box is ticked.

- [ ] **Full test suite green** on the exact commit to be tagged (count recorded in the commit message).
- [ ] **CI green on GitHub** for that commit (all Python/OS cells). It has never run yet.
- [ ] **Account re-checked** read-only: remaining plan seconds >= 360 (probe 10 + Tier A 150 + reserve 200),
      `ibm_marrakesh` operational. The usage period rolled over on 2026-10-08, so re-query.
- [ ] **Draft reviewed**: `ladder_v2_manifest_DRAFT.json`, `ladder_predictions.json`,
      `OPERATING_POINT_ADDENDUM.md`. Any change means regenerating predictions and the hash.
- [ ] **Hash recomputed** after the last edit: `python analysis/draft_preregistration.py` prints the SHA-256
      (draft value at time of writing: `73ac8759bccbaf7fdda7149e5df9ee9dedc9b32b50efbf78503b145a26d06188`;
      it changes if anything in the draft changes).
- [ ] **Real manifest written** with `write_campaign_manifest(..., max_jobs=6, shots=8192,
      usage_budget_seconds=160, max_job_seconds=30, preregistration=...)` into a NEW path under `campaigns/`
      (write-once; never overwrite). Its stored `sha256` equals the recomputed hash.
- [ ] **Git tag `prereg-ladder-v2` created and pushed** on the commit containing the manifest, BEFORE the
      probe job. (HardwareBackend does not yet check the tag; that check is still to be added.)
- [ ] **Probe job run alone first**; billed seconds <= 10. If not, stop and re-plan.
- [ ] Tier A days run one per day in the recorded order; each job's calibration timestamp, physical qubits
      and billed seconds recorded. Tiers B and C stay locked until separate written approval.
