# Claims map

Each row is a claim the evidence supports, with the file that holds the number, the exact figure, and
the limit that must travel with it. "Not supported" rows are claims the paper must not make. Paths are
relative to the `qfim-bench` folder. Manuscript sentences are not mapped yet: they were not provided.

## A. What the software is

| ID | Claim | Evidence | Figure | Limit |
|---|---|---|---|---|
| A1 | The method is a one-shot Grover search over all 2^n itemsets with a classically precomputed marked set; it is not level-wise Apriori. | `README.md` ("What this is, exactly"), `review/AUDIT.md` | n/a | Say "Grover-based frequent itemset search". |
| A2 | No quantum advantage is claimed or shown; the marked set already is the answer. | `README.md`, `examples/dashboard.py` disclaimers | n/a | Classical brute force is the fair baseline. |
| A3 | The package has a tested simulator and noisy-simulator path with no credentials. | `tests/` (184 passed), `results/sim/full_test_run.log` (173 at an earlier commit), CI #1 green on b1f3988 | 184 passed locally on 4acc9d3 | CI on 4acc9d3 and later was not awaited; the 184 count is local. |
| A4 | Hardware submission is guarded: write-once manifest, job cap, usage budget, per-job time limit, hash check in the runners. | `src/qfim_bench/backends.py`, `tests/test_hardware_safety.py`, `tests/test_hardware_batch.py` | 17 mocked tests | The hash check is in the runners, not in `HardwareBackend.run` itself. |

## B. The pitfall the package detects

| ID | Claim | Evidence | Figure | Limit |
|---|---|---|---|---|
| B1 | A random-ansatz start with Hadamard diffusion gives a flat success curve; with matched diffusion it follows sin^2((2r+1)theta). The old "start-state effect" was this mismatch. | `results/sim/start_state_design.json`, `results/sim/audit_phase0.json`, `tests/test_circuit.py` | Noiseless, 30 seeds: mismatched median range 0.016-0.024, matched 0.42-0.78 | Noisy part used 6 seeds, not 30. |
| B2 | The v1 hardware campaign could not test amplification: M=26 of 32 makes r=0 already 0.8125. | `campaigns/uniform_marrakesh/`, `results/sim/audit_phase0.json` | hardware 0.7913-0.8124 vs M/N 0.8125 | Frame as "degenerate regime", not "failed experiment". |

## C. Hardware results (ibm_marrakesh, 2026-10-08, 8192 shots, 5 runs per size)

| ID | Claim | Evidence | Figure | Limit |
|---|---|---|---|---|
| C1 | At n=3 (M=1) Grover amplification works on hardware. | `results/hardware/ladder_v2/analysis.json` | P(r=2) = 0.796 [0.789, 0.803] vs 0.124 at r=0 (6.4x); ideal 0.945 | One device, one sitting. |
| C2 | At n=4 (M=2) it still works, narrowly, and the best iteration count shifts earlier. | `results/hardware/ladder_v2b/analysis.json` | P(r=2) = 0.568 [0.547, 0.589], 4.6x r=0; peak 0.582 at r=1; rule 4 passed by about 0.003 | Say "narrowly"; do not round this to "robust". |
| C3 | At n=5 (M=4) amplification is gone. | `results/hardware/ladder_v2b/analysis.json` | P(r=2) = 0.194 [0.189, 0.199], 1.5x r=0; rules 1-4 all fail | Predicted in advance (H3). |
| C4 | Amplification disappears between about 113 and 668 two-qubit gates at r_opt on this device. | C2, C3; gate counts in the same files | 113 gates (n=4) vs 668 (n=5) | Three sizes only; the boundary is a bracket, not a measured point. |
| C5 | Readout error is small and does not explain the loss. | analysis.json files, readout rows | 0.964-0.992 for all-ones/all-zeros | n/a |
| C6 | An echo (forward-and-back) circuit loses more with size. | analysis.json files, echo rows | 0.671 (n=3), 0.370 (n=4), 0.035 (n=5); floor 0.031 | Ordering was a preregistered hypothesis (H4); it held. |
| C7 | The fitted fidelity per two-qubit gate is about 0.994-0.995 at every size. | analysis.json files (`fit`) | 0.9942, 0.9940, 0.9954; simulator 0.9967 | Interval covers shot noise only; the n=5 fit is least informative. |

## D. Predict-then-measure agreement

| ID | Claim | Evidence | Figure | Limit |
|---|---|---|---|---|
| D1 | The noise model predicts the shape of the amplification curve but overestimates the success probability where amplification matters. | `review/preregistration/ladder_predictions.json`, both analysis.json files | Below band: n=4 r=1,2; n=5 r=1,2; echo at n=3,4. TVD to simulator 0.04-0.14, floor under 0.02, p=0.002 | FakeMarrakesh is one calibration snapshot. |
| D2 | Predictions were fixed before the data. | `review/OPERATING_POINT_CRITERION.md` (commit c25b1b0), manifests (`campaigns/ladder_v2/`, `campaigns/ladder_v2b/`), commits on `main` | hashes 6dcfc075..., ac2958ce... | **No git tag exists.** Write "committed before the experiment", never "tagged". |
| D3 | The simulator discriminates weak from strong noise, and two-qubit gate error dominates. | `results/sim/noise_sensitivity.json` | n=5, M=2, r=2: 0.905 (no noise), 0.587 (x0.25), 0.187 (x1), 0.081 (x2); 2Q off 0.396, other sources off 0.19-0.21 | Simulation only. |

## E. Engineering findings

| ID | Claim | Evidence | Figure | Limit |
|---|---|---|---|---|
| E1 | The `mcz` oracle needs about half the two-qubit gates of the reference oracle and gives higher success. | `results/sim/feasibility_sweep.json` | n=4, M=2: 113 vs 325 gates, 0.710 vs 0.502 | Simulation; hardware used only `mcz`. |
| E2 | The v1 oracle's cost grows exponentially with n; a sparse oracle grows polynomially. | `results/sim/item_count_sweep.csv` | n=10: 587,630 vs 1,830 two-qubit gates per iteration | Transpiled for FakeMarrakesh. |
| E3 | The old F1 values equal the "everything frequent" baseline. | `results/sim/f1_reconciliation.json` | 0.6222 (14/31); 0.931 (27/31) | Do not present F1 as performance. |
| E4 | The inherited post-processing rule gives false positives even for a perfect circuit. | `results/sim/public_dataset.json` | min_support 0.08: 95% of shots on the 6 marked states, precision 0.32 | State which rule produced any F1. |
| E5 | Assuming the wrong M breaks the search. | `results/sim/unknown_m.json` | true M=4, assumed 1: 0.945 -> 0.012 | Ideal circuit; BBHT is the remedy. |
| E6 | A naive TVD interval is unreliable near the shot-noise floor. | `results/sim/tvd_calibration.json` | coverage 0.00-0.015 when true TVD <= 0.02; 0.92-0.95 when >= 0.05 | Use p-values near the floor. |

## F. Claims NOT supported (do not write)

- Quantum advantage or speedup of any kind.
- That the method is Apriori, or level-wise.
- "Preregistered with a tag" or "tagged".
- That amplification "survives to n=5", or that F1 shows quantum benefit.
- Anything about day-to-day drift (all runs in one sitting, deviation D1), other devices, other layouts,
  or scaling beyond n=5.
- That the 6-seed noisy ansatz result represents the full seed distribution.

## G. Deviations to disclose

D1 runs shared one sitting; D2 no git tag; D3 CI not awaited for later commits; D4 code added after
adoption (metadata recording, runners). Details: `review/preregistration/DEVIATIONS.md`.
