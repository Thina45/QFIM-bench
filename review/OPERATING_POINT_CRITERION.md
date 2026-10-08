# Operating-point criterion for the hardware campaign

Written and committed BEFORE running the fixed-M/N feasibility sweep (Phase 2 item 1) and the
cheaper-oracle comparison (item 2). It is fixed from this commit on and is not to be edited after
any result from those two experiments, or any hardware result, has been seen.

## What was already known when this was written

Seen before writing, so stated openly:

- Noiseless simulation matches `sin^2((2r+1)theta)` to <= 1e-4 (Phase 1).
- At n = 5 with M in {1,2,3,4} (uniform start, matched diffusion, current oracle), FakeMarrakesh at
  optimization level 3 peaks at about 0.2 and decays to the 1/32 floor (Phase 1 sparse table).
  This is the reason the sweep over smaller n exists.
- Oracle cost at n = 5 on FakeMarrakesh: 261 two-qubit gates per iteration (M=1) up to 1,368 (M=6).

Nothing was known about n = 2, 3, 4 under noise, or about any alternative oracle synthesis.

## Candidate operating points

A candidate is (n, M, oracle variant, r). Candidates come only from experiments 1 and 2:
(n, M) in {(2,1), (3,1), (4,2), (5,4)}, the oracle variants run in item 2, and r in 0..r_opt+2.
Marked sets follow the fixed rule "first M basis states of Hamming weight 2". Every candidate is
evaluated at optimization level 3 (the hardware setting), 8192 shots, 5 seeded repeats.

## Pass rule (all must hold)

Let `P(r)` be the mean marked-state probability over the 5 repeats and `P0 = P(0)` measured on
the same transpiled configuration.

1. **Amplification, relative:** `P(r_opt) >= 3 * P0`.
2. **Amplification, absolute floor:** `P(r_opt) >= 0.40`.
3. **Beats the noise fixed point:** `P(r_opt) - M/N >= 0.20`, with the 5-repeat standard error
   below 0.01, so the gap is at least 5 standard errors by construction.
4. **Shape:** `P(r_opt)` is the maximum of `P(r)` over the swept r, or within one repeat-SD of it.
   A curve that only rises monotonically to the sweep edge does not pass.

Rule 3 is the one that separates "Grover survived noise" from "noise happened to land near the
marked set". Rules 1 and 2 are deliberately strict because hardware is expected to do worse than
this simulator, not better.

## Selection among passing candidates

Choose the candidate with the fewest transpiled two-qubit gates at `r_opt`. Ties go to the smaller
n, then the smaller M. Fewest gates is the choice because the one thing known about hardware noise
is that it grows with circuit size.

## If nothing passes

No amplification claim is made and no "does Grover work on hardware" experiment is proposed. The
paper is then about where amplification disappears: the transpiled two-qubit-gate count at which
P(r) collapses to the fixed point. Hardware Tier A would then be a characterization of that
boundary, and it needs a separate budget approval.

## What this rule does not do

- It is applied to simulator output only. A pass is not a prediction that hardware will pass.
- It is not revisited after hardware data. The hardware preregistration will cite this file by its
  commit hash.
- It does not choose the number of hardware repeats, days, or shots. Those belong to the Phase 3
  preregistration.
