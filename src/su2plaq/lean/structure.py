"""Structure of the physics problem, proved/certified in Lean (prompts/006 §1, §4, §5).  Skeleton: step 2.L6."""
from __future__ import annotations

import pathlib

from su2plaq._stub import todo
from su2plaq.lean.certify import LeanCert


def export_structure_certificate(out_path) -> pathlib.Path:
    todo("lean.structure.export_structure_certificate")


def check_structure(path, timeout: float = 900.0) -> LeanCert:
    todo("lean.structure.check_structure")


def symmetry_candidates(basis=None) -> list[dict]:
    todo("lean.structure.symmetry_candidates")


def structure_facts() -> dict:
    todo("lean.structure.structure_facts")


def write_structure_json(path=None) -> pathlib.Path:
    todo("lean.structure.write_structure_json")
