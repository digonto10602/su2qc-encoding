"""Lean tables and the native certificate exporter for the spin-network general circuit (steps 3.L2 / 3.L3)."""
from __future__ import annotations

from su2plaq._stub import todo


def coupling_ints(enc) -> list:
    """2 K[partner, code] for the 47 sorted inner codes (exact integers)."""
    return todo("lean_export.coupling_ints")


def angle_ints(enc) -> list:
    """rz angles of build_UB in units of beta / 2, in gate order."""
    return todo("lean_export.angle_ints")


def lean_literals(enc) -> dict:
    """{"coupling": "[...]", "angles": "[...]", "codes": "[...]"}."""
    return todo("lean_export.lean_literals")


def write_lean_tables(path=None):
    """Regenerate the table block of lean/Su2Plaq/SpinNet/Circuit.lean between the generated markers."""
    return todo("lean_export.write_lean_tables")


def export_certificate(qc, enc, kind, alpha, beta, order, out_path):
    """prompts/006 §4 JSON certificate (schema su2plaq-cert-1)."""
    return todo("lean_export.export_certificate")


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0) -> dict:
    """Run the laptop's checker on the exported certificate."""
    return todo("lean_export.certify")
