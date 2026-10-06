import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SAMPLE_CSV = ROOT / "data" / "sample_transactions.csv"


@pytest.fixture(scope="module")
def transactions():
    from qfim_bench.preprocessing import load_transactions

    return load_transactions(str(SAMPLE_CSV))
