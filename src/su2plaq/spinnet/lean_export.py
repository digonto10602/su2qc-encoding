"""Lean tables and the native certificate exporter for the spin-network general circuit (steps 3.L2 / 3.L3)."""
from __future__ import annotations

import pathlib

from su2plaq._stub import todo
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet.walk import GENERAL7, coupling_table, solve_angles


_BEGIN = "-- BEGIN generated"
_END = "-- END generated"
_INT_TOL = 1e-12
CIRCUIT_LEAN: pathlib.Path = pathlib.Path(__file__).resolve().parents[3] / "lean" / "Su2Plaq" / "SpinNet" / "Circuit.lean"


def _as_int(x: float, what: str, tol: float) -> int:
    n = int(round(x))
    if abs(x - n) > tol:
        raise ValueError(f"{what} = {x!r} is not within {tol:g} of an integer")
    return n


def coupling_ints(enc) -> list:
    """2 K[partner, code] for the 47 sorted inner codes (exact integers; ValueError if not within 1e-12 of an integer)."""
    table = coupling_table(enc)
    codes = [int(c) for c in enc.inner_codes()]
    if codes != sorted(codes):
        raise ValueError("enc.inner_codes() is not sorted")
    return [_as_int(2.0 * table[c], f"2K at code {c:08b}", _INT_TOL) for c in codes]


def angle_ints(enc) -> list:
    """rz angles of build_UB in units of beta / 2, in gate order (solved from K at beta = 1; integers within 1e-9)."""
    steps, _ = GENERAL7
    theta, res = solve_angles(steps, coupling_table(enc), 1.0)
    if res > 1e-9:
        raise ValueError(f"GENERAL7 does not reproduce the coupling table: residual {res:.2e}")
    return [_as_int(2.0 * float(t), f"angle {r} in units of beta/2", 1e-9) for r, t in enumerate(theta)]


def _lit(xs) -> str:
    return "[" + ", ".join(str(int(x)) for x in xs) + "]"


def lean_literals(enc) -> dict:
    """{"coupling": "[...]", "angles": "[...]", "codes": "[...]"}: the strings printed verbatim into Circuit.lean."""
    return {"coupling": _lit(coupling_ints(enc)), "angles": _lit(angle_ints(enc)),
            "codes": _lit(int(c) for c in enc.inner_codes())}


def _table_block(enc) -> str:
    lit = lean_literals(enc)
    return "\n".join([
        _BEGIN + " (su2plaq.spinnet.lean_export.write_lean_tables; do not edit by hand)",
        "/-- the 47 valid inner codes (bits 0..3 = j_b j_r j_t j_l, bits 4..7 = corner bits), sorted -/",
        f"def validInnerCodes : List Nat := {lit['codes']}",
        "/-- `2 K[partner, code]` for the codes of `validInnerCodes` -/",
        f"def couplingTable : List Int := {lit['coupling']}",
        "/-- `rz` angles of the phase walk in units of `beta / 2`, in gate order -/",
        f"def angleTable : List Int := {lit['angles']}",
        _END,
    ])


def write_lean_tables(path=None):
    """Regenerate the table block of lean/Su2Plaq/SpinNet/Circuit.lean between the generated markers (ValueError if the
    markers are missing); returns the path."""
    path = pathlib.Path(path) if path is not None else CIRCUIT_LEAN
    text = path.read_text()
    i, j = text.find(_BEGIN), text.find(_END)
    if i < 0 or j < i:
        raise ValueError(f"{path}: markers '{_BEGIN}' / '{_END}' not found")
    new = text[:i] + _table_block(SpinNet()) + text[j + len(_END):]
    if new != text:
        path.write_text(new)
    return path


def export_certificate(qc, enc, kind, alpha, beta, order, out_path):
    """prompts/006 §4 JSON certificate (schema su2plaq-cert-1)."""
    return todo("lean_export.export_certificate")


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0) -> dict:
    """Run the laptop's checker on the exported certificate."""
    return todo("lean_export.certify")
