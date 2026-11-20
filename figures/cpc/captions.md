# Figure caption drafts (CPC revision)

Each draft states what is measured vs. simulated/theoretical, the sample size, and the interval
type, per the project's research standards. Edit freely before the manuscript; these are starting
drafts, not final text.

**Standards applied to every figure (this pass):** serif/STIX math font, 8pt axis labels / 7pt
tick+legend text, 0.8pt axes lines, 1.2pt data lines, Okabe-Ito colour-blind-safe palette with a
FIXED colour-to-meaning mapping across every figure (n=3/4/5 always `#0072B2`/`#D55E00`/`#009E73`;
ibm_marrakesh/ibm_kingston always the same two colours; ideal/noise-model/digital-twin always
solid/dashed/dotted); bold "(a)"/"(b)" panel labels outside the axes (never an in-axes title);
integer ticks on every integer-valued axis (r, n, gate counts); 95% intervals with caps, type
stated per figure below. Every figure is saved as vector PDF (fonts embedded, `pdf.fonttype=42`),
EPS, 1000-dpi LZW-compressed TIFF, and 600-dpi PNG (`figures/cpc/save_utils.py`). Column widths:
single 90mm, 1.5-column 140mm, double 190mm, noted per figure.

## Fig. A — Ladder success probability vs. Grover iteration count r (double column, 190mm)
Three panels (a)/(b)/(c), n=3/4/5. Measured success probability (`ibm_marrakesh`, 2026-10-08, one
sitting — no replication day available for this panel) vs. ideal (statevector) and
FakeMarrakesh-simulated predictions, with the classical query-search baseline (dotted) shown for
comparison. Error bars on the hardware points are 95% t-intervals (4 d.f., 5 repeats). Source:
`results/cpc_revision/phase1a_classical_baseline.csv`.

## Fig. B — Hardware advantage over the classical baseline (single column, 90mm)
Hardware success probability minus the classical query-search baseline probability, per (n, r),
with 95% CI (t-interval, 4 d.f., 5 repeats); the zero line marks no advantage. A q=0 bug in the
classical-baseline formula was found and fixed this round (REPORT.md section 2) — three (tier,
r=0) cells changed from spuriously "beating" classical to correctly tied with it. Source:
`results/cpc_revision/phase1a_classical_baseline.csv`.

## Fig. C — Success probability vs. two-qubit gate count, with the depolarizing fit (double column, 190mm)
Oct-8 data, two panels. **(a)** Measured success probability vs. the transpiled two-qubit gate
count (log x-axis), per ladder size, with the fitted depolarizing curve
`p(g) = f^g p_ideal + (1-f^g) p_noise` overlaid (binomial MLE). **(b)** per-size Grover-fit f vs.
the EXPLORATORY echo-derived f, both with 95% CIs inflated by √(reduced χ²) (reduced χ² = 55-108
per size, 96 global, all far above 1 — this is a phenomenological fit that captures the trend and
the peak-r location, not an exact description of the data within shot noise; see REPORT.md section
4). Global fit (not plotted per-panel; quote in text): f = 0.99443, inflated CI [0.99387, 0.99511].
Source: `results/cpc_revision/phase1b_global_fit.json`, `phase1c_echo_vs_grover_fit.csv`.

## Fig. D — Distributional distance to three references (double column, 190mm)
Total variation distance **(a)** and Hellinger distance **(b)** between the measured hardware
distribution and three references, per (n, r) (integer r ticks 0-4): ideal (solid), the generic
FakeMarrakesh noisy simulator (dashed), and the calibration-day digital twin from Phase 1E
(dotted; qiskit-aer `NoiseModel.from_backend_properties` at the exact Oct-8 calibration snapshot,
gate + readout error only — no thermal relaxation term, since this device's `BackendProperties`
has no `frequency` field). Colour encodes problem size n; linestyle encodes the reference, in one
shared legend above both panels. Source: `results/cpc_revision/phase1d_distances.csv`,
`phase1e_digital_twin.json`.

## Fig. E — Diffusion-operator pitfall (simulated, EXPLORATORY) (single column, 90mm)
SIMULATED (statevector, 30 seeds), not measured on hardware: success probability vs. r (integer
ticks) for matched diffusion (the ladder's actual construction) vs. a mismatched Hadamard
diffusion operator, at M=1 (n=3's marked-set size), as a box plot over seeds (box = IQR, line =
median, whiskers = full range, outliers suppressed). Illustrates that an incorrectly matched
diffusion operator collapses performance regardless of r. Legend moved outside the axes. Source:
`results/sim/start_state_design.json`.

## Fig. F — Day-to-day drift at the H1 cell (r=2), all three sizes (single column, 90mm)
Measured success probability at r=2 (the H1 hypothesis's defined comparison point), for all three
ladder sizes, across three sittings: 2026-10-08, Run 1 (2026-11-19), Run 3 (2026-11-20, ≥12h after
Run 1). Error bars are 95% t-intervals (4 d.f. for the 5-repeat sittings, 2 d.f. for Run 3's 3
repeats). **n=3 points are drawn hollow** (legend: "hollow marker = two-qubit gate count differs,
Run 1: 39, Run 3: 45"): circuits re-transpiled for Run 3 pin the physical-qubit layout, not the
exact gate sequence, since Run 1's transpiled circuits were not saved (REPORT.md section 13); this
gate-count change alone predicts a larger success-probability drop than observed, so the n=3 point
is not clean evidence of drift. n=4 is gate-matched (113=113 two-qubit gates) and is the cleanest
drift evidence in this figure. Source: `results/hardware/ladder_v2(/b)/analysis.json`,
`results/cpc_revision/cpc_runs_analysis.json`.

## Fig. G — Dynamical decoupling on vs. off, n=4 (single column, 90mm)
Measured success probability vs. r (integer ticks), DD on (Run 1 Tier B) vs. DD off (Run 2), n=4,
both `ibm_marrakesh`. H2 (DD improves success at r=1,2) is NOT SUPPORTED: r=1 is significant in the
opposite direction (DD off outperforms DD on). Error bars are 95% t-intervals (4 d.f., 5 repeats).
Legend moved outside the axes (was overlapping the r=1 points). Source:
`results/cpc_revision/cpc_runs_analysis.json`.

## Fig. H — Logical Grover circuit diagram (n=3, M=1, r=1) (double column, 190mm)
The LOGICAL circuit (state preparation, oracle, diffusion, labelled boxes with barriers between
stages, then measurement) for the `ladder_n3_M1_r1` cell — built from the same
`build_start_preparation` / `build_oracle_variant("mcz")` / `build_diffusion` functions the
campaigns actually use, so the diagram matches the real construction exactly. Box labels are
padded with a leading/trailing space so the box width clears qiskit's own per-wire qubit-index
text (previously "1Diffusion" collided on the shortest box). Illustrative of circuit structure
only; not a transpiled or measured result (no physical layout, gate counts, or hardware-specific
detail shown here — see Fig. C/section 9c for transpiled gate counts).

## Fig. I — Fitted effective fidelity vs. calibrated two-qubit error (double column, 190mm)
Two panels, one point per device/session: "Marrakesh 10-08" (ibm_marrakesh, 2026-10-08),
"Marrakesh 11-19" (ibm_marrakesh, Run 1), "Kingston 11-19" (ibm_kingston, Run 4) — short labels on
panel (b)'s x-axis, full device/date in panel (a)'s legend. **(a)** the fitted global depolarizing
f (inflated CI, § Fig. C) vs. the median two-qubit gate error at submission-time calibration,
restricted to the physical-qubit pairs the ladder circuits actually used. **(b)** the effective
error ratio (1 − f) / median two-qubit error, with the inflated-f CI propagated: approximately 3x
at all three points (2.7-3.4x). Reported as an observation from 3 points, not a general law.
Source: `results/cpc_revision/numbers_for_manuscript.json` → `"effective_error_ratio"`,
`phase1b_global_fit.json`, `cpc_run1_fit.json`, `cpc_run4_fit.json`,
`run1_run4_median_2q_error.json`.

## Fig. J — Software architecture (double column, 190mm)
NOT DATA — a diagram of code structure, drawn with matplotlib boxes/arrows from the real module
names in `src/qfim_bench/`. `pipeline.py` orchestrates Layer B, the 5-stage application pipeline
its own docstring defines (`preprocessing.py -> encoding.py -> circuit.py -> {backends} ->
postprocessing.py`, plus `classical.py`/`manifest.py`); `circuit.py`'s stage dispatches to one of
three interchangeable backends sharing one interface (`Backend.run(circuit, shots)`):
`SimulatorBackend` (ideal), `NoisySimulatorBackend` (noise model), `HardwareBackend` (IBM
Quantum). Layer A is the opt-in characterization layer (`search_cost.py`, `statistics.py`,
`intervals.py`, `tvd_calibration.py`, `fit.py`, `noise_analysis.py`, `reproducibility.py`,
`scaling.py`, `noise_scaling.py`) that reads `pipeline.py`'s results rather than being bundled
into every run. Source: `src/qfim_bench/pipeline.py` docstring and imports (read-only).

## Fig. K — Campaign timeline, broken axis: 2026-10-08 (a) / 2026-11-19–20 (b) (double column, 190mm)
NOT DATA — a timeline with a broken x-axis: panel (a) 2026-10-08 (original campaigns), panel (b)
2026-11-19 to 2026-11-20 (Runs 1–4), both with hour-level ticks (IST) and standard diagonal
axis-break marks. One swimlane per campaign; each tick is one job, placed at that job's recorded
CREATION/SUBMISSION time (`results/cpc_revision/job_creation_times.json`, a read-only
`QiskitRuntimeService.job().creation_date` query — NOT `calibration_timestamp`, which precedes
submission and would misplace every job before its own preregistration commit; this was corrected
on review). **Verified and printed by the script before plotting: every Run 1–4 job's creation
time is after the 494632b commit (2026-11-19 14:46:33 IST) — confirmed, no violations.** The
addendum V3 commit (`494632b`, committed and pushed 2026-11-19 14:46:33+05:30, before the first
Run 1 job, created 2026-11-19 14:52:04.949+05:30; REPORT.md section 9b) is a vertical dotted line
in panel (b); the original operating-point criterion + addendum DRAFT (commits `c25b1b0`/
`dd01e6e`, both 2026-10-08) falls inside panel (a)'s date range and is not separately marked there
(panel (a) IS that date). Light teal vertical bands mark each campaign's calibration-snapshot
timestamp (exact moments only, from the manifests — no assumed window duration). Job counts per
campaign: ladder_v2 6, ladder_v2b 10, Run 1 15, Run 2 5, Run 4 15, Run 3 9.

## Fig. L — ibm_marrakesh local qubit layout, Oct-8 vs Run 1 (1.5-column, 140mm)
NOT DATA — the local subgraph of the 156-qubit heavy-hex coupling map (FakeMarrakesh's saved
coupling_map, confirmed identical to the live backend's, 352 edges/same edge set, in a one-off
Phase 0 check; no job submitted to make this figure) containing every physical qubit used at
n=3/4/5 on either date, plus every qubit within 2 coupling-graph hops. Node positions come from
Graphviz "neato" laid out on the FULL 156-qubit graph (conda-forge `graphviz` + `pygraphviz`,
installed this pass), then cropped to the local subgraph — relative positions match the real chip
floorplan exactly, not a schematic. Every drawn qubit is labelled with its index. **Marker SHAPE**
(not just colour) encodes problem size: circle n=3, square n=4, triangle n=5 — so a qubit used by
two sizes shows both outlines overlaid, visibly distinguishable. Physical qubits used by the
gate-bearing (two-qubit-gate) circuits, from the saved manifests' `circuits_info`: **(a)**
2026-10-08 (`campaigns/ladder_v2`, `ladder_v2b`); **(b)** Run 1, 2026-11-19
(`campaigns/cpc_run1`). The three qubit groups (n=3/4/5) sit in disconnected regions of the chip
(no coupling path within 2 hops between them), so each panel shows three separate local
neighbourhoods, not one connected region. Note visible in (a): Tier B (n=4, qubits 98/110/111/112)
and Tier C (n=5, 91/98/110/111/112) share 4 of 5 physical qubits on 2026-10-08, shown as
overlapping square+triangle outlines — an incidental fact about that day's transpilation, not a
control; Run 1 (b) has no such overlap (disjoint qubit sets per size).

## Fig. M — Second device comparison (EXPLORATORY) (double column, 190mm)
Measured success probability vs. r (integer ticks), three panels n=3/4/5: `ibm_marrakesh` (Run 1)
vs. `ibm_kingston` (Run 4), with the ideal curve and the classical query-search baseline (dotted).
Error bars are 95% t-intervals (4 d.f., 5 repeats). EXPLORATORY — no hypothesis about device
ordering was preregistered; kingston's Tier B PASS (section 9c) is a new, unplanned result.
Source: `results/cpc_revision/cpc_runs_analysis.json`,
`cpc_run1_classical_baseline.csv`.

## Fig. N — Output distributions over all basis states (double column, 190mm)
Two rows: **(a)** n=3, M=1, r=2 (8 basis states); **(b)** n=5, M=4, r=1 (32 basis states, every
4th tick labelled). Three bars per basis state: ideal (statevector, exact), FakeMarrakesh (noisy
simulator, same `optimization_level=3`/`seed_transpiler=42`/5 seeds as the original predictions,
`analysis/ladder_predictions.py`), and MEASURED hardware (2026-10-08, one repeat: `day1.json` for
(a), `C_run1.json` for (b), 8192 shots). Marked states shaded. TVD / Hellinger (hardware vs.
ideal / vs. FakeMarrakesh), from `results/cpc_revision/phase1d_distances.csv`: (a) n=3 r=2 —
TVD 0.1494 (vs ideal) / 0.0516 (vs FakeMarrakesh), Hellinger 0.1648 / 0.0519; (b) n=5 r=1 —
TVD 0.5143 (vs ideal) / 0.1198 (vs FakeMarrakesh), Hellinger 0.3789 / 0.0932 — hardware is
markedly closer to FakeMarrakesh than to ideal at n=5, consistent with Fig. D.

## Fig. S1 (supplementary) — Depolarizing-fit residuals vs. r, Oct-8 (single column, 90mm)
Measured minus fitted success probability (per-size fit, Fig. C), per (n, r), integer r ticks.
Reduced chi-square per size (far above 1 at every size — see Fig. C / REPORT.md section 4
goodness-of-fit caveat): n=3 108.4, n=4 83.8, n=5 55.3 (global 96.2).
Source: `results/cpc_revision/phase1b_residuals.csv`, `phase1b_global_fit.json`.
