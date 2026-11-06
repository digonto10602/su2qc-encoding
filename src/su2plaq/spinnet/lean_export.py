"""Lean tables and the native certificate exporter for the spin-network general circuit (steps 3.L2 / 3.L3)."""
from __future__ import annotations

import math
import pathlib
import tempfile
from fractions import Fraction

import numpy as np

from su2plaq._stub import todo
from su2plaq.lean import project
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet.walk import FRAME, GENERAL7, TARGET, coupling_table, mirror, solve_angles


_BEGIN = "-- BEGIN generated"
_END = "-- END generated"
_INT_TOL = 1e-12
_SPINNET_LEAN = pathlib.Path(__file__).resolve().parents[3] / "lean" / "Su2Plaq" / "SpinNet"
CIRCUIT_LEAN: pathlib.Path = _SPINNET_LEAN / "Circuit.lean"
# prompts/102 section 2/3: kernel-checked exact structure (Mathlib-free files), tables rendered from the Python objects
RECOUPLING_LEAN: pathlib.Path = _SPINNET_LEAN / "Recoupling.lean"
SEMANTICS_LEAN: pathlib.Path = _SPINNET_LEAN / "Semantics.lean"
SPECTRUM_LEAN: pathlib.Path = _SPINNET_LEAN / "Spectrum.lean"
BRIDGE_LEAN: pathlib.Path = _SPINNET_LEAN / "Bridge.lean"
GATE_NAMES = ("x", "cx", "rccx", "h", "rz")
_EXACT_BEGIN = "-- BEGIN generated exact"
_EXACT_END = "-- END generated exact"


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


def _lean_op(st) -> str:
    """One GENERAL7 step as a Lean `Op` (rccx is read with Toffoli semantics, as in `classical_slots`)."""
    name, args = st[0], [int(a) for a in st[1:]]
    if name == "x" and len(args) == 1:
        return f".x {args[0]}"
    if name == "cx" and len(args) == 2:
        return f".cx {args[0]} {args[1]}"
    if name == "rccx" and len(args) == 3:
        return f".ccx {args[0]} {args[1]} {args[2]}"
    if name == "rz" and len(args) == 1:
        if args[0] != TARGET:
            raise ValueError(f"rz on wire {args[0]}, the Lean model assumes the frame target {TARGET}")
        return f".rz {args[0]}"
    raise ValueError(f"step {st!r} has no Lean model")


def split_skeleton(steps=None):
    """(compute, walk) of GENERAL7 = compute + walk + mirror(compute): compute = steps before the first rz, walk = the
    rz / cx part up to the uncompute (ValueError if the tail is not exactly mirror(compute))."""
    steps = GENERAL7[0] if steps is None else steps
    first = next((i for i, s in enumerate(steps) if s[0] == "rz"), None)
    if first is None:
        raise ValueError("skeleton has no rz")
    compute = list(steps[:first])
    tail = mirror(compute)
    if list(steps[len(steps) - len(tail):]) != tail:
        raise ValueError("skeleton does not end with mirror(compute)")
    return compute, list(steps[first:len(steps) - len(tail)])


def _ops_literal(ops) -> str:
    return "[" + ", ".join(_lean_op(s) for s in ops) + "]"


def _model_lines() -> list:
    compute, walk = split_skeleton()
    return [
        "/-- the CX frame of `build_walk` (`walk.FRAME`), in gate order -/",
        "def frameCx : List (Nat × Nat) := [" + ", ".join(f"({int(a)}, {int(b)})" for a, b in FRAME) + "]",
        "/-- flag computation of `GENERAL7` (compute half; ancillas `A=8, B=9, F=10, P=11, Q=12, G1=13, G2=14`) -/",
        f"def flagOps : List Op := {_ops_literal(compute)}",
        "/-- the phase walk of `GENERAL7` on the frame target: `rz`, then `rz` conjugated by `cx(F,·)`, `cx(G1,·)`, `cx(G2,·)` -/",
        f"def walkOps : List Op := {_ops_literal(walk)}",
    ]


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
        *_model_lines(),
        _END,
    ])


def write_lean_tables(path=None):
    """Regenerate the table + circuit-model block (tables, frameCx, flagOps, walkOps) of lean/Su2Plaq/SpinNet/Circuit.lean between the generated markers (ValueError if the
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


# ---------------------------------------------------------------------------------------------------------------------
# prompts/102: exact Lean recoupling / gate semantics / spectrum (Mathlib-free files)
# ---------------------------------------------------------------------------------------------------------------------

_N_WIRES = 15
_ARITY = {"x": 1, "cx": 2, "rccx": 3, "h": 1, "rz": 1}          # qubits per gate
_NARGS = {"x": 1, "cx": 2, "rccx": 3, "h": 1, "rz": 2}          # integers per gate tuple (rz: qubit, angle)


def gate_ints(qc) -> list:
    """Gate list of a 15-qubit circuit as integer tuples in program order: ("x", q) | ("cx", c, t) | ("rccx", a, b, t) |
    ("h", q) | ("rz", q, a) with q = qc.find_bit(.).index and a = angle / (beta/2), beta = qc.metadata["beta"].
    ValueError for a gate outside GATE_NAMES, num_qubits != 15 (the outer register is not modelled), a missing/zero beta, or
    an angle not within 1e-9 of an integer multiple of beta/2."""
    if qc.num_qubits != _N_WIRES:
        raise ValueError(f"the exact Lean model has {_N_WIRES} wires, circuit has {qc.num_qubits}")
    beta = qc.metadata.get("beta") if qc.metadata else None
    if beta is None or float(beta) == 0.0:
        raise ValueError("qc.metadata['beta'] must be present and non-zero")
    out = []
    for ins in qc.data:
        op = ins.operation
        if op.name not in GATE_NAMES:
            raise ValueError(f"gate {op.name!r} has no exact Lean model (allowed: {GATE_NAMES})")
        qs = tuple(qc.find_bit(q).index for q in ins.qubits)
        if len(qs) != _ARITY[op.name]:
            raise ValueError(f"gate {op.name!r} on {len(qs)} qubits")
        if op.name == "rz":
            out.append(("rz", qs[0], _as_int(float(op.params[0]) / (float(beta) / 2.0), "rz angle in units of beta/2", 1e-9)))
        else:
            out.append((op.name, *qs))
    return out


def _lean_gate(g: tuple) -> str:
    """One gate tuple as a Lean `Gate` term (negative integers in parentheses)."""
    name, args = g[0], g[1:]
    if name not in GATE_NAMES or len(args) != _NARGS[name]:
        raise ValueError(f"bad gate tuple {g!r}")
    return ".{} {}".format(name, " ".join(f"({a})" if a < 0 else str(a) for a in (int(a) for a in args)))


def gate_literal(qc) -> str:
    """Lean literal "[.cx 1 3, .cx 0 1, ..., .rz 0 (-7), ...]" of `gate_ints(qc)` (negative integers in parentheses)."""
    return "[" + ", ".join(_lean_gate(g) for g in gate_ints(qc)) + "]"


def _exact_recoupling_block(enc) -> str:
    lit = lean_literals(enc)
    return "\n".join([
        _EXACT_BEGIN + " (su2plaq.spinnet.lean_export.write_lean_exact_tables; do not edit by hand)",
        "/-- the 47 valid inner codes (bits 0..3 = j_b j_r j_t j_l, bits 4..7 = corner bits), sorted -/",
        f"def exportedCodes : List Nat := {lit['codes']}",
        "/-- `2 K[partner, code]` for the codes of `exportedCodes` -/",
        f"def exportedTwoK : List Int := {lit['coupling']}",
        _EXACT_END,
    ])


def _replace_block(path: pathlib.Path, begin: str, end: str, block: str) -> pathlib.Path:
    """Replace the text from `begin` to the end of `end` in `path` by `block` (ValueError if a marker is missing)."""
    text = path.read_text()
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < i:
        raise ValueError(f"{path}: markers '{begin}' / '{end}' not found")
    new = text[:i] + block + text[j + len(end):]
    if new != text:
        path.write_text(new)
    return path


def _write_recoupling_tables(path=None) -> pathlib.Path:
    path = pathlib.Path(path) if path is not None else RECOUPLING_LEAN
    return _replace_block(path, _EXACT_BEGIN, _EXACT_END, _exact_recoupling_block(SpinNet()))


def _exact_semantics_block() -> str:
    from su2plaq.circuits.spinnet import build_UB      # local import: circuits.spinnet imports the spinnet package
    return "\n".join([
        _EXACT_BEGIN + " (su2plaq.spinnet.lean_export.write_lean_exact_tables; do not edit by hand)",
        "/-- `build_UB(1.0)` gate list rendered from the Qiskit circuit (rz angles in units of `beta / 2`) -/",
        f"def ubGates : List Gate := {gate_literal(build_UB(1.0))}",
        _EXACT_END,
    ])


def _write_semantics_gates(path=None) -> pathlib.Path:
    path = pathlib.Path(path) if path is not None else SEMANTICS_LEAN
    return _replace_block(path, _EXACT_BEGIN, _EXACT_END, _exact_semantics_block())


def write_lean_exact_tables(recoupling_path=None, semantics_path=None):
    """Regenerate the "-- BEGIN generated exact" / "-- END generated exact" blocks of Recoupling.lean (exportedCodes,
    exportedTwoK) and Semantics.lean (ubGates = gate_literal(build_UB(1.0)); W2); ValueError if markers are missing.
    Returns (recoupling_path, semantics_path)."""
    rec = _write_recoupling_tables(recoupling_path)
    sem = _write_semantics_gates(semantics_path)
    return rec, sem


def lean_eval(body: str, imports: tuple = ("Su2Plaq.SpinNet.Recoupling",), timeout: float = 300.0) -> str:
    """Run `lake env lean` on a temporary file `import <imports>` + `body` (cwd lean/); returns stdout.  RuntimeError with
    stdout + stderr on a non-zero exit.  The imported modules must be built (`lake build Su2Plaq.SpinNet.Recoupling`)."""
    text = "".join(f"import {m}\n" for m in imports) + "\n" + body + "\n"
    with tempfile.TemporaryDirectory(prefix="lean_eval_") as d:
        f = pathlib.Path(d) / "Eval.lean"
        f.write_text(text)
        r = project.lake(["env", "lean", str(f)], timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"lean exited with {r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}")
    return r.stdout


def _lean_lines(out: str, ncols: int) -> list:
    """Lines of `#eval` output that are exactly `ncols` whitespace-separated integers (other lines, e.g. warnings, are
    not data and are ignored; callers check the expected row count)."""
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != ncols:
            continue
        try:
            rows.append([int(x) for x in parts])
        except ValueError:
            continue
    return rows


def lean_sixj_table() -> dict:
    """All (a,b,c,d,e,f) in {0,1,2}^6 (doubled spins) -> float(q * sqrt(r)) of `Su2Plaq.SpinNet.sixj` (exact q, r from Lean,
    one float evaluation here)."""
    body = ("open Su2Plaq.SpinNet in\n"
            "#eval IO.println (String.intercalate \"\\n\" ((List.range 729).map fun i =>\n"
            "  let a := i / 243 % 3; let b := i / 81 % 3; let c := i / 27 % 3; let d := i / 9 % 3; let e := i / 3 % 3; let f := i % 3\n"
            "  let s := sixj a b c d e f\n"
            "  s!\"{a} {b} {c} {d} {e} {f} {s.q.num} {s.q.den} {s.r.num} {s.r.den}\"))")
    rows = _lean_lines(lean_eval(body), 10)
    if len(rows) != 729:
        raise RuntimeError(f"expected 729 rows of Lean sixj output, got {len(rows)}")
    out = {}
    for a, b, c, d, e, f, qn, qd, rn, rd in rows:
        if qd <= 0 or rd <= 0 or rn < 0:
            raise RuntimeError(f"bad Lean sixj row {(a, b, c, d, e, f, qn, qd, rn, rd)}")
        q = Fraction(qn, qd)
        r = Fraction(rn, rd)
        out[(a, b, c, d, e, f)] = float(q) * math.sqrt(float(r))
    return out


def lean_valid_codes() -> list:
    """`#eval validCodes` of Recoupling.lean."""
    body = "open Su2Plaq.SpinNet in\n#eval IO.println (String.intercalate \"\\n\" (validCodes.map toString))"
    rows = _lean_lines(lean_eval(body), 1)
    return [r[0] for r in rows]


def lean_states() -> list:
    """`#eval states` of Recoupling.lean as y + 256 o, in Lean order."""
    body = ("open Su2Plaq.SpinNet in\n"
            "#eval IO.println (String.intercalate \"\\n\" (states.map fun s => toString (s.1 + 256 * s.2)))")
    rows = _lean_lines(lean_eval(body), 1)
    return [r[0] for r in rows]


def lean_gate_images(gate: tuple, n_qubits: int, beta: float) -> np.ndarray:
    """Complex (2^n, 2^n) matrix of one gate from the Lean semantics (`applyBasis`) at z = exp(i beta / 4): column i is the
    image of basis state |i> (little-endian); "h" columns carry the global 1/sqrt(2) that Lean keeps as a count.
    Output rows are `i j m re im` = term (re + i im) z^m of the amplitude of |j> in the image of |i>."""
    if any(not 0 <= int(q) < n_qubits for q in (gate[1:1 + _ARITY.get(gate[0], 0)])):
        raise ValueError(f"gate {gate!r} acts outside {n_qubits} qubits")
    term = _lean_gate(tuple(gate))
    body = ("open Su2Plaq.SpinNet in\n"
            f"#eval IO.println (String.intercalate \"\\n\" ((List.range {2 ** n_qubits}).flatMap fun i =>\n"
            f"  (applyBasis ({term} : Gate) i [(0, 1, 0)]).flatMap fun p =>\n"
            "    p.2.map fun t => s!\"{i} {p.1} {t.1} {t.2.1} {t.2.2}\"))")
    rows = _lean_lines(lean_eval(body, imports=("Su2Plaq.SpinNet.Semantics",)), 5)
    z = np.exp(1j * float(beta) / 4.0)
    mat = np.zeros((2 ** n_qubits, 2 ** n_qubits), dtype=complex)
    for i, j, m, re, im in rows:
        mat[j, i] += complex(re, im) * z ** m
    if gate[0] == "h":
        mat /= math.sqrt(2.0)
    return mat


def export_certificate(qc, enc, kind, alpha, beta, order, out_path):
    """prompts/006 §4 JSON certificate (schema su2plaq-cert-1)."""
    return todo("lean_export.export_certificate")


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0) -> dict:
    """Run the laptop's checker on the exported certificate."""
    return todo("lean_export.certify")
