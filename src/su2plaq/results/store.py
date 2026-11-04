"""Results JSON store (prompts/002 §2.9, §2.11). Stubs (step 0.1)."""
from __future__ import annotations

import pathlib

from su2plaq._stub import todo

SCHEMA_VERSION = 1
RESULT_KEYS = ("schema_version", "encoding", "circuit_id", "kind", "params", "provenance", "verification",
               "metrics", "files", "extra")


def save_result(path, *, encoding, circuit_id, kind, params, verification, metrics, files=None, extra=None) -> pathlib.Path:
    todo("save_result")


def load_result(path) -> dict:
    todo("load_result")
