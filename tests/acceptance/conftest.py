"""Acceptance-test configuration (planner-owned).

- Makes ``src/`` importable without installation.
- Registers the ``slow`` marker so the suite collects without a root pytest.ini.
- Forces single-threaded BLAS / Aer per process so ``pytest -n auto`` does not oversubscribe.
- Provides a fixed seed fixture.
"""
import os
import sys
import pathlib

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest  # noqa: E402

SEED = 20261102


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long-running acceptance test (run at milestone gates)")


@pytest.fixture
def seed():
    return SEED


@pytest.fixture
def results_dir():
    d = _ROOT / "results"
    d.mkdir(exist_ok=True)
    return d
