"""Acceptance-test configuration (LOCKED, planner-owned; prompts/002 §6).

* BLAS threads are forced to 1 before numpy is imported (safe under `pytest -n auto`).
* Lock integrity: tools/check_lock.py (sha256 of every locked file) is run at session start when present;
  the git-tag check `~/.claude/bin/acceptance-check` is the primary guard and is run by the coordinator.
* PENDING rule: a test that hits NotImplementedError / ImportError from the project (not-yet-built module or
  stub) FAILS with a message starting with `PENDING:` instead of erroring at collection.
"""
from __future__ import annotations

import os
import pathlib
import sys
import warnings

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pytest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

SEED = 20261104


def pytest_sessionstart(session):
    try:
        from tools.check_lock import check  # type: ignore
    except Exception:  # tools/ not built yet (step 0.1) — the git-tag check still applies
        warnings.warn("tools/check_lock.py not available; relying on ~/.claude/bin/acceptance-check")
        return
    problems = check(ROOT)
    if problems == ["LOCK.json missing"]:
        warnings.warn("tests/acceptance/LOCK.json missing; run python tools/lock.py m0 m1 m2 (coordinator)")
        return
    if problems:
        raise SystemExit("ACCEPTANCE LOCK BROKEN:\n  " + "\n  ".join(problems))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    try:
        yield
    except (NotImplementedError, ImportError) as exc:  # includes ModuleNotFoundError
        pytest.fail(f"PENDING: {type(exc).__name__}: {exc}", pytrace=False)


@pytest.fixture(scope="session")
def seed() -> int:
    return SEED


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


@pytest.fixture(scope="session")
def root() -> pathlib.Path:
    return ROOT
