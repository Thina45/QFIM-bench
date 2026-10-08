# Open issues (updated at Stop-Gate 1)

## Needs your decision

1. **Ansatz finding is a mismatched-diffusion artefact (AUDIT, decision gate).** Approve reframing it
   as a validation/pitfall result, and approve implementing `diffusion="matched" | "hadamard"` in
   Phase 1. Until you do, no circuit code changes.
2. **Bit-ordering reversal (AUDIT item 4).** `decode_bitstring_to_itemset` reverses the
   item-to-qubit convention. No reported number is affected (symmetric oracle). Approve fixing it in
   Phase 1 so asymmetric marking is safe; four `xfail(strict=True)` cases in `tests/test_ordering.py`
   then become ordinary passing tests.
3. **Algorithm name.** The circuit is a one-shot Grover search with a cardinality oracle, not
   level-wise Apriori (AUDIT item 3). Choose the name to use in the paper and README.

## Could not verify

4. **Review documents missing.** `QFIM-bench_SoftwareX_Action_Plan.docx` and
   `SoftwareX_guide_for_authors.txt` are not on this machine, so the Phase 0 audit did not use them.
   Add them to `review/` if you want them taken into account.
5. **IBM authentication docs.** Checked via a web fetch whose output is a model-written summary.
   The `ibm_quantum_platform` channel and the `instance` recommendation should be re-read on the
   IBM page before being cited.

## Known defects not yet fixed (Phase 1/5)

6. `backends.py` module docstring is stale (says hardware is "not implemented" and the runtime is an
   optional extra). Both are now false.
7. `HardwareBackend` "write-once" manifest is not tamper-evident, and the job cap resets if the
   manifest is deleted and recreated (AUDIT item 5). Phase 3.2 replaces this with a hash check.
8. No `instance` CRN argument, so every IBM call searches all instances.

## Carried forward, not yet addressed

9. Phases 1-6 are not started. Hardware (Phase 3) will not be touched without your approval of a
   QPU-time budget.
10. The v1 campaign (`campaigns/uniform_marrakesh/`) is untouched and is the degenerate M=26 regime
    (r=0 already gives 0.8125). Its hardware values (0.7931, 0.7913, 0.7982, 0.7935, 0.8124) sit
    near, not at, that reference; Phase 4 recomputes the offset in standard errors.
