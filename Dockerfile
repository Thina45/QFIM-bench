# Reproducible environment for qfim-bench: exact tested dependency versions, no credentials needed.
#   docker build -t qfim-bench .
#   docker run --rm qfim-bench                  # runs the test suite, then the quickstart
#   docker run --rm qfim-bench python examples/quickstart.py
# The image never contains an IBM Quantum token and its tests never contact IBM (hardware paths are mocked).
FROM python:3.13-slim

WORKDIR /app
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt pytest-cov

COPY . .
RUN pip install --no-cache-dir -e . --no-deps

ENV IBM_QUANTUM_TOKEN=""
CMD ["sh", "-c", "pytest -q -W ignore --cov=qfim_bench --cov-report=term && python examples/quickstart.py"]
