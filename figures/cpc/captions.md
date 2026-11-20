# Figure caption drafts (CPC revision)

Each draft states what is measured vs. simulated/theoretical and the sample size, per the
project's research standards. Edit freely before the manuscript; these are starting drafts, not
final text.

## Fig. A — Ladder success probability vs. Grover iteration count r
Measured success probability (`ibm_marrakesh`, 2026-10-08, one sitting — no replication day
available for this panel) vs. ideal (statevector) and FakeMarrakesh-simulated predictions, for the
three ladder sizes (n=3, M=1; n=4, M=2; n=5, M=4), with the classical query-search baseline
(dashed) shown for comparison. Error bars on the hardware points are 95% t-intervals (4 d.f., 5
repeats). Source: `results/cpc_revision/phase1a_classical_baseline.csv`.

## Fig. B — Hardware advantage over the classical baseline
Hardware success probability minus the classical query-search baseline probability, per (n, r),
with 95% CI; the zero line marks no advantage. A q=0 bug in the classical-baseline formula was
found and fixed this round (REPORT.md section 2) — three (tier, r=0) cells changed from spuriously
"beating" classical to correctly tied with it. Source:
`results/cpc_revision/phase1a_classical_baseline.csv`.

## Fig. C — Success probability vs. two-qubit gate count, with the depolarizing fit
Measured success probability vs. the transpiled two-qubit gate count, per ladder size, with the
fitted depolarizing curve `p(g) = f^g p_ideal + (1-f^g) p_noise` overlaid (binomial MLE, Oct-8
data). EXPLORATORY echo-circuit fidelity shown alongside (triangles). The annotated global-fit CI
is inflated by √(reduced χ²) (reduced χ² = 96, far above 1 — this is a phenomenological fit that
captures the trend and the peak-r location, not an exact description of the data within shot
noise; see REPORT.md section 4). Source: `results/cpc_revision/phase1b_global_fit.json`,
`phase1c_echo_vs_grover_fit.csv`.

## Fig. D — Distributional distance to ideal and to the noisy simulator
Total variation distance and Hellinger distance between the measured hardware distribution and (i)
the ideal distribution and (ii) the generic FakeMarrakesh noisy-simulator distribution, per (n, r).
Source: `results/cpc_revision/phase1d_distances.csv`.

## Fig. E — Diffusion-operator pitfall (simulated, EXPLORATORY)
SIMULATED (statevector, 30 seeds), not measured on hardware: success probability vs. r for matched
diffusion (the ladder's actual construction) vs. a mismatched Hadamard diffusion operator, at
M=1 (n=3's marked-set size), as a box plot over seeds. Illustrates that an incorrectly matched
diffusion operator collapses performance regardless of r. Source:
`results/sim/start_state_design.json`.

## Fig. F — Day-to-day drift at the H1 cell (r=2), all three sizes
Measured success probability at r=2 (the H1 hypothesis's defined comparison point), for all three
ladder sizes, across three sittings: 2026-10-08, Run 1 (2026-11-19), Run 3 (2026-11-20, ≥12h after
Run 1). Error bars are 95% t-intervals (4 d.f. for the 5-repeat sittings, 2 d.f. for Run 3's 3
repeats). **n=3 points are drawn hollow**: Run 3's n=3 circuit has 45 two-qubit gates vs. Run 1's
39 (circuits re-transpiled for Run 3 pin the physical-qubit layout, not the exact gate sequence,
since Run 1's transpiled circuits were not saved — REPORT.md section 13); this gate-count change
alone predicts a larger success-probability drop than observed, so the n=3 point is not clean
evidence of drift. n=4 is gate-matched (113=113 two-qubit gates) and is the cleanest drift evidence
in this figure. Source: `results/hardware/ladder_v2(/b)/analysis.json`,
`results/cpc_revision/cpc_runs_analysis.json`.

## Fig. G — Dynamical decoupling on vs. off, n=4
Measured success probability vs. r, DD on (Run 1 Tier B) vs. DD off (Run 2), n=4, both
`ibm_marrakesh`. H2 (DD improves success at r=1,2) is NOT SUPPORTED: r=1 is significant in the
opposite direction (DD off outperforms DD on). Error bars are 95% t-intervals (4 d.f., 5 repeats).
Source: `results/cpc_revision/cpc_runs_analysis.json`.

## Fig. H — Transpiled circuit diagram (n=3, r=1)
The transpiled `ladder_n3_M1_r1` circuit (optimization_level=3, seed_transpiler=42), drawn against
FakeMarrakesh — confirmed identical in coupling-map topology to the live `ibm_marrakesh` backend at
the time of a one-off read-only check (352 edges, same edge set). Illustrative, not a measured
result.

## Fig. I — Fitted effective fidelity vs. calibrated two-qubit error
Two panels, one point per device/session (ibm_marrakesh 2026-10-08, ibm_marrakesh Run 1
2026-11-19, ibm_kingston Run 4 2026-11-19). **(a)** the fitted global depolarizing f (inflated CI,
§ Fig. C) vs. the median two-qubit gate error at submission-time calibration, restricted to the
physical-qubit pairs the ladder circuits actually used. **(b)** the effective error ratio
(1 − f) / median two-qubit error, with the inflated-f CI propagated: approximately 3x at all three
points (2.7-3.4x). Reported as an observation from 3 points, not a general law. Source:
`results/cpc_revision/numbers_for_manuscript.json` → `"effective_error_ratio"`,
`phase1b_global_fit.json`, `cpc_run1_fit.json`, `cpc_run4_fit.json`,
`run1_run4_median_2q_error.json`.
