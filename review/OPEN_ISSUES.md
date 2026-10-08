# Open issues (updated during Phase 2)

## Needs your decision or action

1. **Push status.** `main` was pushed by you at `fce4b0e`. Every later commit is local only. The
   shell this work runs in has credentials for a different GitHub account and gets a 403, so you push:
   `git push origin main`. No tags have been created by this work.
2. **Version.** `pyproject.toml` and `__version__` were 0.1.0; `CITATION.cff` and the paper say 1.0.1.
   All three now say 1.0.1. The code on `main` is well ahead of the released v1.0.1 (new circuit
   builders, new defaults), so the next real release should be 1.1.0. Decide before tagging.
3. **Contradiction in `manuscript/manuscript_scope_note.md`** (not edited, as instructed). It says the
   paper's hardware used the ansatz start. The campaign manifest
   (`campaigns/uniform_marrakesh/manifest.json`) says "Uniform start H^5|0>". The hardware used the
   uniform start. The note also says the ansatz "does not exhibit the amplification signal"; that was a
   mismatched-diffusion artefact (AUDIT). Delete or rewrite the note.
4. **`SoftwareX_guide_for_authors.txt` does not exist anywhere under `Software_X_journal`.** The Action
   Plan `.docx` is in `review/`. The word limit (3,000 or 4,000) is still unknown.
5. **Operating-point decision (Stop-Gate 3).** The preregistered rule, applied mechanically, selects
   n=2, M=1, `mcz` oracle (2 two-qubit gates at r_opt). That is a two-qubit toy. See the Stop-Gate 3
   report for what that does and does not mean. Nothing about hardware has been decided.

## Resolved in this phase

- Ansatz result reframed as a mismatched-diffusion pitfall; `diffusion="matched"|"hadamard"` implemented.
- Bit-ordering reversal fixed; the four xfails are ordinary passing tests.
- Algorithm named "Grover-based frequent itemset search" (not Apriori; one-shot over 2^n itemsets).
- `backends.py` docstring corrected; `instance` forwarded to `QiskitRuntimeService`.
- README hardware section and modules table no longer say HardwareBackend is a stub.
- `config.py` docstring rewritten; `grover_iterations` default is now `None` (r_opt from M).
- Noisy-simulator optimization level now defaults to 3, the hardware level. The archived v1 scripts pin
  level 1 so their committed numbers still reproduce.
- CI workflow added (`.github/workflows/ci.yml`): Python 3.10-3.13 on Linux/macOS/Windows, pinned
  qiskit 2.1.2 / aer 0.17.2 / runtime 0.41.1, coverage percentage, no token in the environment.
  **It has not been run.** The YAML parses; whether the matrix is green is unknown until GitHub runs it.
- `HardwareBackend` takes the job cap and shot count from the manifest (`max_jobs`, `shots`). Manifests
  without them (the archived v1) fall back to the legacy 5 jobs / 8192 shots. A SHA-256 manifest hash
  is implemented and tested (`manifest_hash`, `verify_manifest_hash`) but **not enforced**: `run()` does
  not call it yet.
- F1 numbers reconciled (`analysis/f1_reconciliation.py`): 0.4516/1.0/0.6222 is the conference dataset
  (14 of 31 itemsets frequent), 0.871/1.0/0.931 is the bundled sample data (27 of 31). Both equal the
  "everything frequent" baseline for their dataset.
- Synthetic dataset relabelled `item_1..item_12`; public UCI Online Retail subset added with license
  and citation in `data/README.md`.

## Still open

6. **Manifest is not yet tamper-evident in practice.** Hash check exists but is unused, and deleting
   and recreating the manifest still resets the job count. Phase 3 enforces the hash against a git tag.
7. **Dashboard noisy-simulator column** (`campaigns/uniform_marrakesh/noisy_sim_seeded.json`) was made
   at optimization level 1; the hardware used level 3. The file is archived as-is. Regenerating it at
   level 3 would change a committed number, so it needs your call.
8. **Post-processing rule.** The inherited containment-count rule (itemset is "frequent" if the counts of
   all measured states containing it reach tau) gives false positives even for a perfect circuit: on the
   public data at min_support 0.08 the noiseless circuit puts 95% of shots on the 6 marked states, yet
   precision is 0.32 because supersets of marked states accumulate counts. The null-derived
   detection rule (`detected_states`) has no such effect. The README states the inherited rule; the
   paper text should say which one produced any F1 it reports.
9. **Cardinality-marking F1 can exceed the baseline by coincidence.** On the sample data at
   min_support 0.05 the v1 cardinality oracle gives F1 0.962 against the everything-frequent 0.931,
   because every itemset of size >= 2 happens to be frequent there. The oracle is data-independent, so
   the same circuit would return the same states on any dataset. Not evidence of a quantum benefit.
10. **Interval scope.** The 95% intervals in the feasibility sweep and the fidelity fit cover shot noise
    only: the transpile is fixed by `seed_transpiler` per cell, so routing/layout variability is not in
    them. The bootstrap on the decay fit assumes the model form is right.
11. **Phase 2A noisy part uses 6 ansatz seeds, not 30.** The 30-seed requirement is met for the
    noiseless distribution (exact). Each noisy ansatz run takes tens of seconds; the script resumes and
    can be extended with `--noisy-seeds 30`.
12. **n=2 is degenerate.** For N=4, M=1, three Grover iterations compose to the identity, so the
    transpiled r=3 circuit has no gates and "survives noise" trivially. n=2 results are not evidence
    about hardware scaling.
13. **Phase 3 (hardware) is not started.** No job has been submitted. It needs your approval of a QPU
    budget. The v1 campaign (`campaigns/uniform_marrakesh/`) is untouched.
