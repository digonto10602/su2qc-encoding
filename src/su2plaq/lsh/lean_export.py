"""Lean tables and native certificate export for the LSH encoding (prompts/400 section 2; docs/METHODS-lsh.md L10).
Step 7.L2: the integer tables and the circuit model of lean/Su2Plaq/LSH/Circuit.lean (`coupling_ints`, `partner_ints`,
`angle_ints`, `lean_literals`, `write_lean_tables`).  Step 7.L3 (`export_certificate`, `certify`, `write_pins`) is a STUB."""
from __future__ import annotations

import pathlib

from su2plaq.lsh import walk as W

ROOT = pathlib.Path(__file__).resolve().parents[3]
CIRCUIT_LEAN = ROOT / "lean" / "Su2Plaq" / "LSH" / "Circuit.lean"
_BEGIN = "-- BEGIN generated"
_END = "-- END generated"
_N_TRANS, _N_FRAME = len(W.TRANSCODE), len(W.FRAME)


def _pending(name: str, step: str):
    raise NotImplementedError(f"PENDING: su2plaq.lsh.lean_export.{name} is not built yet (prompts/400 step {step})")


def _as_int(x: float, what: str) -> int:
    r = round(x)
    if abs(x - r) > 1e-9:
        raise ValueError(f"{what} = {x!r} is not an integer")
    return int(r)


def coupling_ints(enc) -> list:
    """2 K[partner, code] for the sorted inner codes (0 for dark codes)."""
    table = W.coupling_table(enc)
    return [_as_int(2 * table[int(c)], f"2K at inner code {int(c)}") for c in enc.inner_codes()]


def partner_ints(enc) -> list:
    """Partner inner code of every sorted inner code (the code itself for dark codes)."""
    partner = W.partner_table(enc)
    return [int(partner.get(int(c), int(c))) for c in enc.inner_codes()]


def angle_ints(enc) -> list:
    """rz angles of build_UB in units of beta/2, in gate order (the solved angles are integer multiples of beta/2)."""
    steps, _ = W.skeleton(0)
    theta, res = W.solve_angles(steps, W.coupling_table(enc), 1.0)
    if res > 1e-9:
        raise ValueError(f"walk skeleton does not reproduce the coupling table (residual {res:.2e})")
    return [_as_int(2 * float(t), "angle / (beta/2)") for t in theta]


def _ints(xs) -> str:
    return "[" + ", ".join(str(int(x)) for x in xs) + "]"


def lean_literals(enc) -> dict:
    """The four integer tables as Lean list literals (verbatim in Circuit.lean)."""
    return {"codes": _ints(enc.inner_codes()), "coupling": _ints(coupling_ints(enc)),
            "partner": _ints(partner_ints(enc)), "angles": _ints(angle_ints(enc))}


def _op(st) -> str:
    name = st[0]
    if name == "cx":
        return f".cx {st[1]} {st[2]}"
    if name == "x":
        return f".x {st[1]}"
    if name == "rccx":
        return f".ccx {st[1]} {st[2]} {st[3]}"          # Toffoli semantics on bits (the relative phase is diagonal)
    if name == "rz":
        return f".rz {st[1]}"
    raise ValueError(f"no Lean Op for step {st!r}")


def _ops(steps) -> str:
    return "[" + ", ".join(_op(st) for st in steps) + "]"


def circuit_segments() -> dict:
    """Classical skeleton of U_B split into the segments Circuit.lean models: transcoder, frame, flags, walk.  The
    layout transcoder | frame | h | flags | walk | flags^-1 | h | frame^-1 | transcoder^-1 is asserted."""
    steps, _ = W.skeleton(0)
    a = _N_TRANS + _N_FRAME
    n_flags = (len(steps) - 2 * a - 2 - 10) // 2
    trans, frame = steps[:_N_TRANS], steps[_N_TRANS:a]
    flags, walk = steps[a + 1:a + 1 + n_flags], steps[a + 1 + n_flags:a + 11 + n_flags]
    if (steps[a][0] != "h" or [x[0] for x in walk] != ["rz", "cx", "rz", "cx", "cx", "rz", "cx", "cx", "rz", "cx"]
            or steps[a + 11 + n_flags:a + 11 + 2 * n_flags] != W.mirror(flags) or steps[a + 11 + 2 * n_flags][0] != "h"
            or steps[a + 12 + 2 * n_flags:] != W.mirror(frame) + W.mirror(trans)):
        raise ValueError("skeleton(0) does not have the layout transcoder|frame|h|flags|walk|flags^-1|h|frame^-1|transcoder^-1")
    return {"trans": trans, "frame": frame, "flags": flags, "walk": walk}


def _table_block(enc) -> str:
    lit = lean_literals(enc)
    seg = circuit_segments()
    return (f"{_BEGIN} (su2plaq.lsh.lean_export.write_lean_tables; do not edit by hand)\n"
            f"def lshInnerCodes : List Nat := {lit['codes']}\n"
            f"def lshCoupling : List Int := {lit['coupling']}\n"
            f"def lshPartner : List Nat := {lit['partner']}\n"
            f"def lshAngles : List Int := {lit['angles']}\n"
            f"def transOps : List Op := {_ops(seg['trans'])}\n"
            f"def frameOps : List Op := {_ops(seg['frame'])}\n"
            f"def flagOps : List Op := {_ops(seg['flags'])}\n"
            f"def walkOps : List Op := {_ops(seg['walk'])}\n")


def write_lean_tables(path=None):
    """Regenerate the block between `-- BEGIN generated` and `-- END generated` of lean/Su2Plaq/LSH/Circuit.lean (ValueError if
    the markers are missing); returns the path."""
    from su2plaq.encodings.lsh import LSH

    path = pathlib.Path(path) if path is not None else CIRCUIT_LEAN
    text = path.read_text()
    i, j = text.find(_BEGIN), text.find(_END)
    if i < 0 or j < i:
        raise ValueError(f"{path}: markers '{_BEGIN}' / '{_END}' not found")
    new = text[:i] + _table_block(LSH()) + text[j:]
    if new != text:
        path.write_text(new)
    return path


def export_certificate(qc, enc, kind, alpha, beta, order, out_path):
    _pending("export_certificate", "7.L3")


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0) -> dict:
    _pending("certify", "7.L3")


def write_pins(path=None):
    _pending("write_pins", "7.L3")
