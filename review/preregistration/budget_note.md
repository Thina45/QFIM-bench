# QPU budget facts (read-only account query, 2026-10-08; nothing submitted)

- Plan limit: 600 quantum seconds per usage period. Consumed 68 s, remaining 532 s. The reported period
  (2026-09-10 to 2026-10-08 11:28 UTC) ends at about the time of the query, so a new period may begin
  with the full 600 s; re-query before adopting a plan.
- The 68 s was spent by the 5 archived v1 jobs (r=1,2,2,3,4; 5 qubits, 8192 shots, deep circuits):
  about 13.6 s per job. Those circuits were far deeper (hundreds to thousands of layers more) than the
  ladder circuits, so most of that is likely per-job overhead plus the 250 us repetition delay, not gate
  time. That is an inference from one data point, not a measurement of the ladder.
- `ibm_marrakesh` was operational with 0 pending jobs; `ibm_fez` (2 pending) and `ibm_kingston` (1) were also available.

## Consequence for the draft

The draft proposes 120 circuit-runs (24 circuits x 5 days). Run as 120 single-circuit jobs at roughly
10-14 s each that is 1200-1700 s, **over the 600 s limit**. Run as 5 jobs of 24 circuits each (one
`SamplerV2` job with 24 PUBs per day) the estimate is about 5 x (24 x 2.1 s + overhead) = 250-300 s,
inside the limit. `HardwareBackend` currently submits one circuit per job, so a multi-circuit mode has
to be added and tested (mocked) before adoption. Tier A alone (n=3, 40 runs, about 84 s of execution)
fits in a single period with room to spare.

The 2.1 s per circuit is scheduled circuit duration plus repetition delay for 8192 shots, from
FakeMarrakesh. The true billed time is unknown until one small job is measured, which needs approval.
