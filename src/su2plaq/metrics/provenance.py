"""Run provenance: every number that leaves the project carries commit, versions, platform and seeds (docs/METHODS.md §8)."""
from __future__ import annotations

import datetime
import os
import pathlib
import platform
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _git(*args) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=_ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _version(mod: str) -> str:
    import importlib
    import importlib.metadata as md

    try:
        return md.version(mod.replace("_", "-"))
    except md.PackageNotFoundError:
        m = importlib.import_module(mod)
        return str(getattr(m, "__version__", "unknown"))


def provenance(seeds: dict | None = None) -> dict:
    """{"git_commit","git_dirty","versions":{...},"platform","cpu_count","seeds","timestamp_utc"}.
    git_commit = `git rev-parse --short HEAD` ("unknown" outside a repository); git_dirty = uncommitted tracked changes."""
    commit = _git("rev-parse", "--short", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "git_commit": commit if commit else "unknown",
        "git_dirty": bool(status) if status is not None else None,
        "versions": {"python": sys.version.split()[0], "numpy": _version("numpy"), "scipy": _version("scipy"),
                     "qiskit": _version("qiskit"), "qiskit_aer": _version("qiskit_aer"),
                     "pygridsynth": _version("pygridsynth")},
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "seeds": dict(seeds) if seeds else {},
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
