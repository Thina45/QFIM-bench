# qfim-bench

Reproducible benchmarking of Grover-based frequent itemset search.

## What this is, exactly

`qfim-bench` runs a **one-shot Grover search over all 2^n candidate itemsets**. The set of basis
states to amplify (the oracle's marked set) is **precomputed classically**, from classical support,
from an itemset-size rule, or given explicitly. Grover iterations amplify that set on a simulator
(or IBM hardware), and the measured bitstrings are **scored classically**. It is not level-wise
Apriori: there is no downward-closure pruning, and support is never evaluated by the quantum
circuit. Because the marked set is already the answer, **this package does not offer a quantum
advantage**; it demonstrates and benchmarks the search step and provides the measurement tooling
(statistics, noise comparison, repeat-run checks, circuit-cost accounting, manifest-gated hardware
submission) around it. For small item counts, brute-force enumeration of the 2^n subsets is the
fair classical baseline.

## Install

```bash
pip install -e .            # simulator-only use: qiskit, qiskit-aer, mlxtend, pandas
pip install -e ".[hardware]" # adds qiskit-ibm-runtime for IBM Quantum hardware (not yet implemented)
pip install -e ".[dev]"      # adds pytest
```

For an exact environment, use `requirements.txt` (versions used for the paper's software checks).

## Quickstart (no credentials)

```bash
python examples/quickstart.py
```

Runs the full pipeline on `data/sample_transactions.csv` (synthetic, 300 baskets) on the Aer
simulator in a sparse regime (`min_support=0.25` marks 6 of 32 states, `r_opt = 1`). It prints the
theoretical and empirical success probability (about 0.95) and precision/recall/F1 **next to the
trivial baselines** ("everything frequent", random guess), so a score is never read without
knowing what doing nothing clever achieves. The default `min_support=0.05` marks 27 of 32 states, a
dense regime where Grover cannot help.

## Modules

| Module | Purpose |
|---|---|
| `config.py` | `QFIMConfig`: every run parameter, validated |
| `circuit.py` | Grover circuit `(D·O)^r·A`, oracles (support-driven, cardinality, explicit), matched/Hadamard diffusion, closed-form and exact success probability |
| `marking.py` | Classically precomputed marked sets (`support`, `cardinality`, `explicit`) |
| `statistics.py` | Run summaries (mean, SD, CV, CI), total variation distance, bootstrap TVD |
| `backends.py` | `SimulatorBackend`, `NoisySimulatorBackend` (FakeMarrakesh), `HardwareBackend` (stub) |
| `preprocessing.py` | Transaction loading (ragged rows), frequency ranking, reduction to top-k items |
| `encoding.py` | Itemset ↔ qubit ↔ bitstring convention: `item_order[p]` ↔ qubit `p` ↔ bit `p` of the basis index |
| `postprocessing.py` | Containment support, threshold τ = ⌈σ·S·α⌉, precision/recall/F1, trivial baselines, null-derived detection threshold |
| `classical.py` | Brute force, Apriori, ECLAT, FP-Growth, with runtime and peak memory |
| `noise_analysis.py` | Pairwise distribution comparison across backends |
| `reproducibility.py` | Repeated-run check with summary statistics |
| `scaling.py` | Circuit-size sweep and oracle accounting (depth, two-qubit gates per M) with hard, process-killing timeouts |
| `pipeline.py` | `run_qfim_bench(config)` end-to-end |

## Diffusion and start state: a pitfall this package detects

Grover amplification needs the diffusion operator to reflect about **the state the iteration starts
from**. `diffusion="matched"` (the default) is `A(2|0><0|-I)A†`, correct for any start state `A`.
`diffusion="hadamard"` is `H^n(2|0><0|-I)H^n`, a reflection about the *uniform* state. The two are
identical for `initial_state="uniform"`. For `initial_state="ansatz"` (a bound EfficientSU2) the
Hadamard diffusion is **mismatched**: it does not amplify the marked set, and the success
probability stays flat.

Exact noiseless values, N = 32, M = 26 marked (the v1 cardinality oracle), ansatz seed 42:

| r | uniform start (= theory) | ansatz, Hadamard diffusion (mismatched) | ansatz, matched diffusion |
|---|---|---|---|
| 0 | 0.8125 | 0.8087 | 0.8087 |
| 1 | 0.0508 | 0.8000 | 0.0446 |
| 2 | 0.3840 | 0.8215 | 0.4078 |
| 3 | 1.0000 | 0.8208 | 0.9993 |
| 4 | 0.3972 | 0.7996 | 0.3549 |

The flat curve is therefore caused by the operator mismatch, not by the start state or by hardware
noise. The v1 ansatz experiments used the mismatched operator; it remains available
(`diffusion="hadamard"`) so that behaviour is reproducible, and `tests/test_circuit.py` pins it.
With a matched diffusion the ansatz follows `sin²((2r+1)θ_A)`, `θ_A = asin(√P_A)`, exactly.

The v1 operating point (M = 26 of 32) is also **degenerate**: r = 0 already gives 0.8125, so r = 2
(0.384) is worse than not running Grover at all, and a noisy device that drifts toward the uniform
distribution also lands near 0.80. Use a sparse marked set (for example M = 1–4 of 32, r near
`optimal_iterations(M, N)`) to make amplification observable. See `review/AUDIT.md`.

## Configuration

All run parameters live in `QFIMConfig` (`config.py`): dataset path, `top_k_items`, `marking`
(`"support"` data-driven, the default; `"cardinality"` the v1 size rule; `"explicit"` with
`marked_states`), `oracle_threshold` (cardinality only), `grover_iterations` (`None` means
`r_opt` from the classically known M), `diffusion` (`"matched"` or `"hadamard"`), `initial_state`,
`ansatz_reps`, `shots`, `min_support`, `alpha`, `backend`, `seed`. Nothing downstream hardcodes
these values.

## Reproducibility

- Ansatz angles: `numpy.random.seed(seed)` then `uniform(-π, π)` in `qc.parameters` order.
- Simulator RNG: `seed_simulator=seed`.
- Transpiler: `seed_transpiler=42` when transpiling.
- The package stores counts and metadata for every run, so results can be re-analysed without
  re-running a backend (`noise_analysis.compare_counts`).

## Hardware

`HardwareBackend` currently raises `NotImplementedError`. The paper's hardware runs used
`ibm_marrakesh`, `SamplerV2` in backend mode, optimization level 3, dynamical decoupling (XpXm), and
8,192 shots. The hardware path will be implemented and tested against those settings in a later
release; it costs real QPU time and needs `IBM_QUANTUM_TOKEN`.

## Generic layer demo (no QFIM code)

`examples/generic_bell_demo.py` runs an ordinary two-qubit Bell circuit using only the simulator
backend and the statistics helpers. It imports no QFIM-specific module, and shows that the generic
layer works on any circuit:

```bash
python examples/generic_bell_demo.py
```

## Known limitations

- Association rules are generated by `generate_association_rules` (textbook confidence and lift, checked against a hand-computed example). An earlier "zero rules" result was a bug in the old rule step; the sample dataset yields 36 rules at confidence ≥ 0.5.
- Post-processing uses the paper's inherited threshold, α = 0.1, which makes τ = 41 counts out of
  8,192 shots. This is permissive by design; see the paper's limitations.
- The sample dataset is synthetic. The paper's Kaggle dataset is not redistributed here.

## Tests

```bash
pytest
```

The test suite runs on simulators only (no credentials). It checks the paper's theoretical values
and post-processing metrics, the uniform-start circuit against theory, the classical algorithms
against brute force, and the noisy backend's ordering relative to the paper's hardware counts.

## Citation

See `CITATION.cff`.

## License

Apache-2.0. See `LICENSE.txt`.
