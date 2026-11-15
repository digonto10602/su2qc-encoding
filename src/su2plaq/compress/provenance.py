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
    "encodings/registry.py",
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


def evaluator_files(encoding: str | None = None) -> list[pathlib.Path]:
    """The shared files (existing ones, in `EVALUATOR_FILES` order) followed by the files the registry lists for `encoding`
    (prompts/008 §4).  An encoding that is not registered has no files of its own.  A registered own file that does not exist is an
    error (a registry typo must not silently shrink a hash)."""
    from su2plaq.encodings import registry

    files = [_SRC / f for f in EVALUATOR_FILES if (_SRC / f).exists()]
    info = registry.lookup(encoding) if encoding is not None else None
    if info is not None:
        own = [_SRC / f for f in info.evaluator_files]
        missing = [str(f.relative_to(_SRC)) for f in own if not f.exists()]
        if missing:
            raise FileNotFoundError(f"evaluator files of encoding {encoding!r} missing under src/su2plaq: {missing}")
        files += own
    return files


def code_hash_for(encoding: str | None = None) -> str:
    """`code_hash` of `evaluator_files(encoding)`: shared list + that encoding's own files.  For twelve (and for an encoding that
    is not registered) it equals `code_hash()`."""
    return code_hash(files=evaluator_files(encoding))


def stamp_hash(encoding: str | None = None) -> str:
    """What the archive records as `Entry.evaluator_sha256`: `code_hash_for(encoding)` for an encoding registered with
    stamp "encoding", else the shared `code_hash()`."""
    from su2plaq.encodings import registry

    info = registry.lookup(encoding) if encoding is not None else None
    return code_hash_for(encoding) if info is not None and info.stamp == "encoding" else code_hash()


def package_versions() -> dict:
    """Versions of the packages whose behaviour enters a cached metric: qiskit (lowering / transpile), qiskit-aer (engine
    cross-check) and pygridsynth (T counts of every rotation)."""
    from su2plaq.metrics.provenance import _version

    return {"qiskit": _version("qiskit"), "qiskit_aer": _version("qiskit_aer"), "pygridsynth": _version("pygridsynth")}


def versions_tag(versions: dict | None = None) -> str:
    """12-hex tag of `package_versions()` (or of the given dict); part of the result-cache key (audit 004 N7)."""
    v = package_versions() if versions is None else versions
    return hashlib.sha256(repr(sorted(v.items())).encode()).hexdigest()[:12]


def cache_path(evaluator_sha, program_sha, spec_sha, root=None, versions: dict | None = None) -> pathlib.Path:
    """<root>/compress/cache/<evaluator_sha>/<program_sha>-<spec_sha>-<versions_tag>.json  (any code edit changes the
    evaluator sha; an upgrade of qiskit / qiskit-aer / pygridsynth changes the tag)."""
    root = pathlib.Path(root) if root is not None else ROOT
    return root / "compress" / "cache" / str(evaluator_sha) / f"{program_sha}-{spec_sha}-{versions_tag(versions)}.json"


def machine() -> str:
    import os

    return f"{platform.node()} {platform.machine()} cpus={os.cpu_count()}"
