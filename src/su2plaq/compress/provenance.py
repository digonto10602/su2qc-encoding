"""Evaluator code hash, cache paths and machine description (prompts/002 §2.10)."""
from __future__ import annotations

import hashlib
import pathlib
import platform

ROOT = pathlib.Path(__file__).resolve().parents[3]
_SRC = ROOT / "src" / "su2plaq"

# Explicit list of the files whose content decides what a verdict or a metric is.  Files that do not exist (yet) are skipped.
EVALUATOR_FILES = [
    "compress/builder.py", "compress/evaluate.py", "compress/metrics.py", "compress/synth.py", "compress/passes.py",
    "compress/archive.py", "compress/spec.py", "compress/oracle.py",
    "evaluate/evaluator.py", "evaluate/sparse_sim.py", "evaluate/aer_check.py",
    "metrics/logical.py", "metrics/cliffordt.py",
    "encodings/base.py", "encodings/twelve.py", "exact/operators.py", "exact/physical.py",
    "su2/algebra.py", "su2/wigner.py", "geometry.py",
]


def code_hash(files: list[pathlib.Path] | None = None) -> str:
    """sha256 over the contents (and file names) of an explicit file list (default: EVALUATOR_FILES under src/su2plaq)."""
    if files is None:
        files = [_SRC / f for f in EVALUATOR_FILES if (_SRC / f).exists()]
    h = hashlib.sha256()
    for f in files:
        f = pathlib.Path(f)
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def cache_path(evaluator_sha, program_sha, spec_sha, root=None) -> pathlib.Path:
    """<root>/compress/cache/<evaluator_sha>/<program_sha>-<spec_sha>.json  (any code edit changes the evaluator sha)."""
    root = pathlib.Path(root) if root is not None else ROOT
    return root / "compress" / "cache" / str(evaluator_sha) / f"{program_sha}-{spec_sha}.json"


def machine() -> str:
    import os

    return f"{platform.node()} {platform.machine()} cpus={os.cpu_count()}"
