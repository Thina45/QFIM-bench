# Contributing

Thanks for looking at qfim-bench. It is a research benchmark, so correctness and honest reporting matter
more than features.

## Set up

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-lock.txt && pip install -e . --no-deps
pip install pytest-cov
pytest -q -W ignore --cov=qfim_bench
```

The full suite takes several minutes because it runs noisy simulations. No test contacts IBM Quantum;
hardware code is tested with mocks. Do not put an API token in any file: the package reads
`IBM_QUANTUM_TOKEN` from the environment.

## Rules for changes

- **Add a test with every behaviour change.** If you fix a bug, add a test that fails without the fix.
- **Do not weaken a tolerance to make a test pass.** Tolerances are derived (shot noise, rounding); say how
  a new one was derived.
- **Report negative results.** Experiments live in `analysis/`, are seeded, write raw counts and a manifest to
  `results/`, and are not tuned after seeing hardware data.
- **Hardware is guarded.** Anything that can submit a job must go through `HardwareBackend`, which needs a
  write-once manifest. Never add a path that bypasses it. Archived campaigns under `campaigns/` are not edited.
- **Keep claims honest.** The package does not show a quantum advantage and is not level-wise Apriori.
  See `review/CLAIMS_MAP.md` for what may and may not be claimed.

## Pull requests

Small, focused commits; describe what changed and how you checked it. CI (`.github/workflows/ci.yml`) runs
Python 3.10-3.13 on Linux, macOS and Windows.

Licence: contributions are accepted under Apache-2.0.
