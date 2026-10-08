# Phase 0 audit: qfim-bench v1.0.1 (branch `evidence-v2`)

Evidence: `analysis/audit_phase0.py` (seed 42), outputs in `results/sim/audit_phase0.json` and
`results/sim/audit_phase0_noisy.json`, regression test `tests/test_ordering.py`. No circuit code
was changed in this phase and no hardware job was submitted.

Not available on this machine: `QFIM-bench_SoftwareX_Action_Plan.docx` and
`SoftwareX_guide_for_authors.txt`. The audit therefore does not use them (see OPEN_ISSUES.md).

---

## DECISION GATE (ansatz): triggered

The original `initial_state="ansatz"` result was produced by a **mismatched diffusion operator**.
`build_grover_circuit` builds one Hadamard diffusion and applies it to every start state
(`circuit.py:250`, `diffusion = build_diffusion(n_items)`). Reflection about the uniform state is not
a reflection about the ansatz state, so the Grover iteration is not an amplitude amplification of the
marked subspace for that start. "Start-state effect" is therefore **not a scientific finding**. It
must be reframed as a validation/pitfall result. Numbers are under item 1(c).

---

## 1. How the circuit is built

**(a) Oracle** (`circuit.py:151-181`). Marked states are all bit patterns with Hamming weight >=
`threshold` (`_marked_bitstrings`, lines 136-148), enumerated classically, one multi-controlled X
onto an ancilla in |-> per marked state (X gates flip the zero-valued controls). So marked states are
precomputed classically from the cardinality rule; the oracle never looks at transactions. Cost is
O(M) multi-controlled gates, i.e. about 2^n for the default threshold, which is the reason circuit
size grows so fast with item count.

**(b) Diffusion for `uniform`** (`circuit.py:184-206`). H^n X^n (C^{n-1}Z) X^n H^n. Verified
numerically to equal `2|s><s| - I` with `|s>` uniform, maximum error 1.5e-16 up to a global phase
(`A_diffusion_is_uniform_reflection`). Correct for the uniform start.

**(c) Diffusion for `ansatz`**. The **same** Hadamard operator. It is **not** the matched
`A(2|0><0| - I)A†`. Verified two ways: a numpy model using the Hadamard diffusion reproduces the
package circuit's exact statevector to 7e-13 for both start states (`B_package_vs_numpy_model`).

Exact noiseless P(marked) for the package as written (ansatz seed 42), against the matched variant
and Eq. (4) with `theta_A = asin(sqrt(P_A))`:

| case | r=0 | r=1 | r=2 | r=3 | r=4 |
|---|---|---|---|---|---|
| M=26 uniform (= Eq. 4) | 0.8125 | 0.0508 | 0.3840 | 1.0000 | 0.3972 |
| M=26 ansatz, Hadamard diffusion (current) | 0.8087 | 0.8000 | 0.8215 | 0.8208 | 0.7996 |
| M=26 ansatz, matched diffusion | 0.8087 | 0.0446 | 0.4078 | 0.9993 | 0.3549 |
| M=3 uniform (= Eq. 4) | 0.0937 | 0.6460 | 0.9998 | 0.6742 | 0.1118 |
| M=3 ansatz, Hadamard diffusion (current) | 0.0384 | 0.0368 | 0.0552 | 0.0687 | 0.0589 |
| M=3 ansatz, matched diffusion | 0.0384 | 0.3113 | 0.6957 | 0.9644 | 0.9586 |

With matched diffusion the ansatz curve follows `sin^2((2r+1) theta_A)` exactly and the flatness
disappears. The flat curve is entirely a mismatched-diffusion artefact. (Single seed here; Phase 2A
covers >= 30 seeds. The M=3 marked set is a seeded random choice, indices in the JSON.)

EfficientSU2 settings: `efficient_su2(n, entanglement="linear", reps=1)` decomposed
(`circuit.py:124`), parameters bound by `bind_parameters` (`circuit.py:84-95`) with
`numpy.random.seed(seed)` then `uniform(-pi, pi)` in `qc.parameters` order. Checked across
versions: seed 42 gives the identical ansatz state (same SHA-256 of the rounded amplitudes,
P_A(M=26) = 0.808696) on Qiskit 2.1.2 and 2.5.2, so the angle protocol is reproducible across those
two releases.

## 2. Empty set, singletons, and where M comes from

`M = count_marked_states(n, threshold) = sum_{k>=threshold} C(n,k)` (`circuit.py:38-46`). **M depends
only on `n` and `oracle_threshold`.** `min_support` never reaches the circuit; it is used only in
post-processing (`tau = ceil(min_support * shots * alpha)`, `postprocessing.py`). With threshold 2 the
empty set (weight 0) and all singletons (weight 1) are unmarked, so the oracle does not encode
"support >= sigma" at all. By definition the empty set has support 1.0, so a support oracle would
mark it; this one does not. `mine_frequent_itemsets` scores only non-empty subsets
(`all_nonempty_subsets`), so the empty set is excluded at post-processing, not in the circuit.

## 3. Is it level-wise Apriori?

**No.** It is a one-shot Grover search over all 2^n basis states with a Hamming-weight (cardinality)
oracle. There is no downward-closure pruning, no candidate generation by joining, and no quantum
support evaluation. Frequency is determined classically afterwards by containment counting on the
measured bitstrings. The honest name is "Grover search over a cardinality-defined candidate set with
classical support scoring". For n = 5, brute-force enumeration of the 31 subsets is the fair classical
baseline, and it is trivially cheap.

## 4. Qubit and bit ordering: **inconsistent** (test added)

Convention in the code: `_marked_bitstrings` and `encode_itemset_to_bitstring` put `item_order[p]`
at string index p, and the oracle acts on qubit p, so `item_order[p] <-> qubit p`. Qiskit count keys
print classical bit 0 as the **rightmost** character, so qubit p appears at index `n-1-p`.
`decode_bitstring_to_itemset` (`encoding.py:35-45`) maps index p to `item_order[p]`, which reverses
the convention. Experiment (`D_ordering`): flipping only qubit 0 gives key `00001`, which the package
decodes as `item_4`, not `item_0`.

Consequence: the Hamming-weight oracle and the uniform start are permutation symmetric, so no
success probability reported so far is affected. The reversal changes item labels in the
precision/recall step for the asymmetric ansatz states, and it becomes a live bug for any asymmetric
marking (the planned sparse-marking option). The middle qubit (index 2 of 5) maps to itself, which is
why a test on a single arbitrary qubit can miss it. `tests/test_ordering.py` pins the Qiskit
convention (passing) and checks all five qubits (four are marked `xfail(strict=True)` until the fix is
approved).

## 5. What `HardwareBackend` enforces today

Code: `backends.py:130-272`. Enforced: the manifest file must exist and contain a non-empty
`predictions` dict (`_load_manifest`, line 214); job count in the manifest must be below `max_jobs`
(line 254); shots must equal 8192 (line 255); circuit must have no free parameters; real submission
needs a token. The manifest records `written_utc`, `note`, `predictions`, and per job `label`,
`job_id`, `target` only.

Not enforced: **"write-once" is by existence check at creation only** (`write_campaign_manifest`,
line 285 raises `FileExistsError`). The file is rewritten in full after every job (`_save_manifest`,
line 227) and nothing hashes, signs or version-controls it, so predictions can be edited or the file
deleted and recreated, which also resets the job cap. Predictions are not checked against
timestamps. Not recorded: job timestamps, calibration snapshot, qubit layout, transpiled
depth/2Q count, optimisation level, mitigation flags, seed, counts (the runner script saves counts
separately). The module docstring (`backends.py:1-16`) is stale: it says hardware is not implemented
and that the runtime is an optional extra.

## 6. Versions and IBM authentication

Installed: qiskit 2.1.2, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.41.1, numpy 2.3.2, scipy 1.18.1,
pandas 2.3.2, mlxtend 0.25.0, Python 3.13.5. (A clean install resolves newer releases, e.g. qiskit
2.5.2, so the pin file matters.)

Authentication: the backend calls `QiskitRuntimeService(channel="ibm_quantum_platform", token=...)`
with the token read from `IBM_QUANTUM_TOKEN` (`backends.py:174-180`). This worked live on 2026-10-05
(backend lookup and five job submissions). IBM's initialisation guide
(quantum.cloud.ibm.com/docs/en/guides/initialize-account, fetched for this audit, summarised by the
fetch tool, so re-check before relying on it) states `ibm_quantum_platform` is the default channel,
and it recommends passing an `instance` CRN; with none, every call searches all instances, which
explains the repeated "Default instance not set" lookups. The docs list no environment-variable
route, so `IBM_QUANTUM_TOKEN` is this package's own convention. Recommendation: add an optional
`instance` argument.

## Table 2 reproduction (seed 42, 8192 shots, N=32, M=26)

| r | analytical | noiseless sim | FakeMarrakesh sim |
|---|---|---|---|
| 0 | 0.8125 | 0.8186 | 0.8120 |
| 1 | 0.0508 | 0.0507 | 0.8027 |
| 2 | 0.3840 | 0.3839 | 0.8036 |
| 3 | 0.99995 | 0.9999 | 0.8052 |
| 4 | 0.3972 | 0.3938 | 0.8022 |

Analytical values and the seeded noisy values match the paper exactly. The r=0 row is the point:
doing nothing already gives 0.8125, so r=2 (0.384) is worse than not running Grover, and a noisy
device that drifts toward the uniform distribution lands near 0.80 at every r. At M=26 the noise
response and the ideal r=0 value are the same number, so this regime cannot separate "no
amplification" from "amplification destroyed by noise". That is why the old operating point is
degenerate. (Sampled r=0 differs from 0.8125 by 1.4 standard errors, as expected.)
