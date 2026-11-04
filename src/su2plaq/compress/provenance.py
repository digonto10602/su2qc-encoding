"""Evaluator code hash and cache paths (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

import pathlib

from su2plaq._stub import todo

EVALUATOR_FILES: list[str] = []  # explicit list of evaluator/physics source files, filled in step 2.3/2.4


def code_hash(files: list[pathlib.Path] | None = None) -> str:
    todo("code_hash")


def cache_path(evaluator_sha, program_sha, spec_sha, root=None) -> pathlib.Path:
    todo("cache_path")
