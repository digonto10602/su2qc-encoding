"""Results JSON store (prompts/002 §2.9, §2.11; prompts/003 §4). One JSON file per circuit, keys in RESULT_KEYS order.

`verification` is a dict (a `Verdict` is converted with `verdict_to_dict`).  Besides the fixed keys it may carry the optional
keys engine, engine_accuracy, certified, tolerances, dropped_total, gauss_residual; `save_result` accepts both forms.
Non-finite floats are written as JSON Infinity/NaN (Python json), complex numbers as [re, im].
"""
from __future__ import annotations

import dataclasses
import json
import pathlib

import numpy as np

from su2plaq.metrics.provenance import provenance

SCHEMA_VERSION = 1
RESULT_KEYS = ("schema_version", "encoding", "circuit_id", "kind", "params", "provenance", "verification", "metrics",
               "files", "extra")
_VERDICT_KEYS = ("ok", "reason", "op_norm_error", "max_leak", "dirty_ancilla", "phase", "outer_bits_read", "n_blocks",
                 "gauss_residual", "method", "engine", "engine_accuracy", "certified", "tolerances", "dropped_total",
                 "seconds", "n_inputs")


def _jsonable(x):
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return _jsonable(dataclasses.asdict(x))
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, (complex, np.complexfloating)):
        return [float(x.real), float(x.imag)]
    if isinstance(x, pathlib.Path):
        return str(x)
    return x


def verdict_to_dict(v) -> dict:
    """Evaluator `Verdict` -> the JSON `verification` block (phase as [re, im], failing_inputs kept under that key)."""
    d = {k: getattr(v, k) for k in _VERDICT_KEYS if hasattr(v, k)}
    d["failing_inputs"] = list(getattr(v, "failing_inputs", []))
    return _jsonable(d)


def save_result(path, *, encoding, circuit_id, kind, params, verification, metrics, files=None, extra=None,
                seeds: dict | None = None) -> pathlib.Path:
    """Write results JSON with provenance; returns the path."""
    if not isinstance(verification, dict):
        verification = verdict_to_dict(verification)
    doc = {"schema_version": SCHEMA_VERSION, "encoding": encoding, "circuit_id": circuit_id, "kind": kind,
           "params": params, "provenance": provenance(seeds), "verification": verification, "metrics": metrics,
           "files": files if files is not None else {}, "extra": extra if extra is not None else {}}
    assert tuple(doc) == RESULT_KEYS
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(doc), indent=2) + "\n")
    return path


def load_result(path) -> dict:
    d = json.loads(pathlib.Path(path).read_text())
    if tuple(d) != RESULT_KEYS:
        raise ValueError(f"{path}: keys {list(d)} differ from RESULT_KEYS")
    if d["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{path}: schema_version {d['schema_version']} != {SCHEMA_VERSION}")
    return d
