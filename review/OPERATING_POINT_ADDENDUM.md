# Addendum to the operating-point criterion

`review/OPERATING_POINT_CRITERION.md` (commit c25b1b0) is unchanged and is not edited by this file.
This addendum is committed before any hardware job exists, and it is fixed from its own commit on.

## Why an addendum

Applied mechanically, the criterion's selection rule ("fewest two-qubit gates among passing
candidates") picks (n=2, M=1, `mcz` oracle): 2 two-qubit gates at r_opt. At n=2, N=4, M=1, three
Grover iterations compose to the identity, so the transpiler removes the r=3 circuit entirely. A
2-qubit, 2-CZ result says nothing about how amplification scales on hardware. The rule did what it
was written to do; what it was written to do is not what the paper needs.

## What replaces the single operating point

1. **n=2 is a positive control only.** It checks that the hardware path (transpile, submit, decode
   bit order, analyse) works end to end where the ideal answer is 1.0 at r=1. No scaling claim rests on it.
2. **The experiment is a ladder.** (n, M) = (3,1), (4,2), (5,4), all with M/N = 1/8 and r_opt = 2,
   oracle style `mcz`, uniform start, matched diffusion, r = 0..r_opt+2 (= 0..4), marked set = first M
   basis states of Hamming weight 2. The three points differ only in size, which isolates circuit
   size as the variable. The simulator predicts two-qubit counts at r_opt of 39, 113, 668.
3. **Controls at every ladder point:**
   - a depth-matched echo circuit at r_opt (state preparation plus r_opt iterations, a barrier, then
     the exact inverse; ideal outcome all zeros with probability 1), which measures how much of the
     loss is circuit size independent of the Grover structure;
   - a readout baseline (no gates, and X on every qubit), which measures measurement error.
4. **Predictions are fixed in advance with tolerance bands.** Each ladder cell's prediction is its
   FakeMarrakesh (optimization level 3, 8192 shots, 5 repeats) mean from
   `results/sim/feasibility_sweep.json`; echo and readout predictions come from
   `analysis/ladder_predictions.py`. The band is

   half-width = 5 * sqrt(p (1 - p) / 8192) + 0.05

   The first term is five standard deviations of shot noise. The 0.05 is an allowance, chosen now, for
   the simulator being a single calibration snapshot of a device that drifts. Values are in
   `review/preregistration/ladder_predictions.json`.
5. **How outcomes are read.** Inside the band: the noise model predicted the hardware at that cell.
   Below the band: the hardware is worse than the model. Above it: better. Each is reported. A cell
   where simulator and hardware both sit at the noise floor is not counted as agreement, which is the
   weakness of the earlier M=26 campaign.
6. **A collapse at (5,4) is a valid outcome.** The simulator predicts P(r_opt) = 0.279 against an ideal
   of 0.945 there, and a P(r) curve that never rises above about 0.39. If hardware agrees, the finding
   is where amplification disappears (between about 100 and 700 two-qubit gates), not a failed run.

## Hypotheses, stated before data

- H1 (n=3): the criterion's rules 1-4 are met at r_opt = 2 (P >= 3 x P(r=0), P >= 0.40, gap over M/N
  of at least 0.20, peak at r_opt within one SD).
- H2 (n=4): same rules; the simulator predicts a pass with margin 0.71 vs 0.40.
- H3 (n=5): the rules are not met.
- H4: the echo circuit's P(all zeros) falls with two-qubit count in the order n=3 > n=4 > n=5.
- H5: hardware readout baseline is within its band (0.985-0.991 predicted).

None of H1-H5 is assumed true. A hardware miss on any of them is reported as such.

## What this does not decide

Backend availability, the QPU budget, the number of repeats and days, and whether to run all three
tiers are listed in `review/preregistration/ladder_v2_manifest_DRAFT.json` as a proposal and need the
user's approval. The draft is not used by `HardwareBackend` and nothing has been submitted.
