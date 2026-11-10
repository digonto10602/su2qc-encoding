"""Lean tables and native certificate export for the LSH encoding (prompts/400 section 2). STUB (step 7.0): functions
raise NotImplementedError until steps 7.L2 (tables) and 7.L3 (certificate, pins)."""
from __future__ import annotations


def _pending(name: str, step: str):
    raise NotImplementedError(f"PENDING: su2plaq.lsh.lean_export.{name} is not built yet (prompts/400 step {step})")


def coupling_ints(enc) -> list:
    _pending("coupling_ints", "7.L2")


def partner_ints(enc) -> list:
    _pending("partner_ints", "7.L2")


def angle_ints(enc) -> list:
    _pending("angle_ints", "7.L2")


def lean_literals(enc) -> dict:
    _pending("lean_literals", "7.L2")


def write_lean_tables(path=None):
    _pending("write_lean_tables", "7.L2")


def export_certificate(qc, enc, kind, alpha, beta, order, out_path):
    _pending("export_certificate", "7.L3")


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0) -> dict:
    _pending("certify", "7.L3")


def write_pins(path=None):
    _pending("write_pins", "7.L3")
