# qfim-bench

Reproducible benchmarking of Grover-based quantum frequent itemset mining (QFIM).

`qfim-bench` builds the Grover-based search circuit used in our hardware-characterization study,
runs it on a simulator (or, later, IBM Quantum hardware), mines frequent itemsets from the measured
bitstrings, and scores them against exact classical ground truth. It also provides the statistics,
noise-comparison, reproducibility, and complexity-scaling tools used in the accompanying paper.

**This package does not claim quantum advantage.** It is a measurement and reproducibility tool.

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
simulator and prints the theoretical and empirical success probability and precision/recall/F1.

## Modules

| Module | Purpose |
|---|---|
| `config.py` | `QFIMConfig`: every run parameter, validated |
| `circuit.py` | Grover circuit `(D·O)^r·U_init`, oracle, diffusion, theoretical success probability (Eq. 4) |
| `statistics.py` | Run summaries (mean, SD, CV, CI), total variation distance, bootstrap TVD |
| `backends.py` | `SimulatorBackend`, `NoisySimulatorBackend` (FakeMarrakesh), `HardwareBackend` (stub) |
| `preprocessing.py` | Transaction loading (ragged rows), frequency ranking, reduction to top-k items |
| `encoding.py` | Itemset ↔ bitstring encoding |
| `postprocessing.py` | Containment support, threshold τ = ⌈σ·S·α⌉, precision/recall/F1 |
| `classical.py` | Brute force, Apriori, ECLAT, FP-Growth, with runtime and peak memory |
| `noise_analysis.py` | Pairwise distribution comparison across backends |
| `reproducibility.py` | Repeated-run check with summary statistics |
| `scaling.py` | Circuit-size sweep over candidate-item count, with timeout recording |
| `pipeline.py` | `run_qfim_bench(config)` end-to-end |

## Start state: simulator release vs. hardware study

`qfim-bench` ships with **`initial_state="uniform"` as the default**. This is a deliberate
scope decision for the public software release, not an oversight:

- The uniform start $H^{\otimes n}|0\rangle$ is what Eq. (4)'s theoretical success-probability
  formula assumes. On a noiseless simulator, `qfim-bench` reproduces that curve to within
  sampling noise — this is a claim the package can verify completely, with no QPU access, and
  the test suite checks it (`tests/test_circuit.py`).
- The companion paper's *hardware* runs instead start from a random EfficientSU2 ansatz
  (`initial_state="ansatz"`, seed 42), which is still fully supported here for reproducing that
  paper's exact circuit. But that start state gives a flat ~0.80–0.82 success probability across
  Grover iterations **even on the noiseless simulator** — before any hardware noise is
  introduced. That is a property of the circuit's start state, not of NISQ noise, so shipping it
  as the package's default/example would make `qfim-bench`'s own documented behaviour look like
  a bug (a flat curve with no amplification) rather than the honest, reproducible result it is.

| r | Eq. (4) theory | uniform start, noiseless sim | ansatz start (paper's hardware circuit), noiseless sim |
|---|---|---|---|
| 1 | 0.0508 | 0.0507 | 0.7965 |
| 2 | 0.3840 | 0.3839 | 0.8193 |
| 3 | 0.99995 | 0.9999 | 0.8202 |
| 4 | 0.3972 | 0.3938 | 0.7980 |

**What this means for using the package:**

- `QFIMConfig()` (default) and `examples/quickstart.py` use `initial_state="uniform"` and
  demonstrate genuine Grover amplification on the simulator, matching Eq. (4).
- `QFIMConfig(initial_state="ansatz", seed=42)` reproduces the companion paper's actual hardware
  circuit for anyone validating or extending that paper's results.
- A hardware characterization run with `initial_state="uniform"` has not yet been performed (it
  requires QPU time and is planned as follow-up work) — only that run would test the paper's
  original "NISQ noise erases the amplification signal" claim as stated, since that claim
  presumes the uniform-start/Eq.-4 regime. The ansatz-start hardware results already collected
  do not test that claim; they characterize a different (flat-by-construction) circuit under
  noise, which is still a valid and useful result (see `NoisySimulatorBackend` and the
  `noisy_closer_to_hardware_reference_than_ideal` test), just not the amplification-vs-noise one.

This separation — a fully simulator-verified default behaviour, with the paper's hardware-study
configuration available but explicitly opt-in — is also why `HardwareBackend` stays a stub in
this release: shipping a software package should not imply a hardware claim that hasn't been
run under the configuration the claim requires.

## Configuration

All run parameters live in `QFIMConfig` (`config.py`): dataset path, `top_k_items`,
`oracle_threshold`, `grover_iterations`, `shots`, `min_support`, `alpha`, `ansatz_reps`,
`initial_state`, `backend`, `seed`. Nothing downstream hardcodes these values.

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

## Known limitations

- Classical association-rule counts are not reported: rules returned zero at confidence ≥ 0.5 on
  the datasets tested, and that result has not yet been checked against an independent implementation.
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
