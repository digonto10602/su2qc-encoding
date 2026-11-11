"""Lean tables and the native certificate exporter for the spin-network general circuit (steps 3.L2 / 3.L3)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import subprocess
import tempfile
import time
from fractions import Fraction

import numpy as np

from su2plaq.lean import certify as C
from su2plaq.lean import exact as E
from su2plaq.lean import pins as PN
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


# ---------------------------------------------------------------------------------------------------------------------
# Native certificate (step 3.L3): exact route-B data over K = Q(i, sqrt2, sqrt3), the laptop's JSON schema su2plaq-cert-1
# (prompts/006 section 4), checked by the spin-network checker `su2plaq_cert_spinnet` (lean/Su2PlaqCert/SpinNet/, which
# reuses the laptop's replay/compare code and pins its own states/targets).  Exporter helpers of su2plaq.lean.certify /
# .exact / .pins are used read-only.
ROOT = pathlib.Path(__file__).resolve().parents[3]
CERT_DIR = ROOT / "results" / "spinnet" / "certs"
SPIN_PINS_FILE = ROOT / "lean" / "Su2PlaqCert" / "SpinNet" / "Pins.lean"
CHECKER_TARGET = "su2plaq_cert_spinnet"
N_DATA, N_OUTER = 8, 8                  # canonical frame: data i -> i, outer j -> 8 + j, ancilla k -> 16 + k (= the circuit's own)
SPIN_TARGETS = (("UE", 1), ("UB", 1), ("step", 1), ("step", 2))
_CERT_TOL = 1e-12
_PREFER = {"UE": "a", "UB": "b", "step": "ab"}
_EXACT_CACHE: dict = {}
_BUILT = False


def target_base(kind: str, order: int = 1) -> tuple:
    """(d_alpha, d_beta): theta_alpha = alpha / d_alpha, theta_beta = beta / d_beta of `exact_target_blocks`
    (z_beta = exp(i beta / 4) makes every eigenvalue lambda in {0, +-1/2, +-1, +-2} of H_B an integer exponent -4 lambda)."""
    return (8 if (kind == "step" and order == 2) else 4, 4)


def exact_states(enc) -> list:
    """The 433 physical states as exact K-vectors in the form of `su2plaq.lean.exact.exact_encoded_states`: unit vectors
    [{"codes": int64[1], "amps": [K(1)]}] indexed by the label index k."""
    return [{"codes": np.array([int(c[0])], dtype=np.int64), "amps": [E.K_ONE]} for c in enc.physical_vectors().codes]


def _exact_hb(enc) -> dict:
    """{(i, j): K} nonzero entries of the route-B H_B^phys (433 x 433): couplings are recognised as rationals of denominator
    <= 2 within 1e-12 (they are -2, -1/2, 1), raising otherwise; the matrix must be real symmetric."""
    HB = enc.h_magnetic()
    if np.abs(HB.imag).max() > _CERT_TOL or np.abs(HB - HB.T).max() > _CERT_TOL:
        raise E.ExactError("H_B^phys is not real symmetric")
    out = {}
    for i, j in zip(*np.nonzero(np.abs(HB) > _CERT_TOL)):
        x = float(HB[i, j].real)
        q = Fraction(x).limit_denominator(2)
        if abs(x - float(q)) > _CERT_TOL:
            raise E.ExactError(f"H_B[{i},{j}] = {x!r} is not a rational with denominator <= 2")
        out[(int(i), int(j))] = E.KNum(q)
    return out


def _blocks_of(n: int, H: dict) -> list:
    """Connected components of the graph of H (sorted index lists, ordered by their smallest index)."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for (i, j) in H:
        parent[find(i)] = find(j)
    groups: dict = {}
    for k in range(n):
        groups.setdefault(find(k), []).append(k)
    return sorted(groups.values(), key=lambda g: g[0])


def _n_inner_half(enc) -> list:
    """Number of inner links with j = 1/2 for every state k (bits 0-3 of its code); cross-checked against the float H_E."""
    codes = [int(c[0]) for c in enc.physical_vectors().codes]
    nel = [bin(c & 0xF).count("1") for c in codes]
    err = float(np.abs(enc.h_electric() - 0.75 * np.array(nel)).max())
    if err > _CERT_TOL:
        raise E.ExactError(f"inner electric energy differs from 3/4 x #(j=1/2 inner links) by {err}")
    return nel


def exact_target_blocks(enc, kind: str, order: int = 1) -> list:
    """Exact route-B target in blocks [{"ks": [...], "entries": [(i, j, Laurent)]}], V[ks[i], ks[j]] a Laurent polynomial in
    (z_alpha, z_beta) over K with base `target_base(kind, order)`: U_E = diag(z_alpha^{-3 n}) (n = number of inner links with
    j = 1/2, z_alpha = exp(i alpha / 4)); U_B = sum_lambda P_lambda z_beta^{-4 lambda} from the exact spectral projectors of
    each connected block of H_B^phys (K = Q(i, sqrt 2, sqrt 3)); step = U_B U_E (order 1) or U_E(alpha/2) U_B U_E(alpha/2)
    (order 2, d_alpha = 8).  Cross-checked against `enc.target` at (0.37, 0.61) (<= 1e-12 per entry)."""
    if kind not in ("UE", "UB", "step"):
        raise ValueError(f"unknown target kind {kind!r}")
    if kind == "step" and order not in (1, 2):
        raise ValueError(f"order must be 1 or 2, got {order}")
    order = order if kind == "step" else 1
    key = (enc.name, kind, order)
    if key in _EXACT_CACHE:
        return _EXACT_CACHE[key]
    n = len(enc.labels)
    nel = _n_inner_half(enc)
    blocks = []
    if kind == "UE":
        for k in range(n):
            blocks.append({"ks": [k], "entries": [(0, 0, E.Laurent.mono((-3 * nel[k], 0), E.K_ONE))]})
    else:
        H = _exact_hb(enc)
        for ks in _blocks_of(n, H):
            pos = {k: i for i, k in enumerate(ks)}
            Hb = [[E.KNum(0) for _ in ks] for _ in ks]
            for (i, j), v in H.items():
                if i in pos:
                    Hb[pos[i]][pos[j]] = v
            proj = E.spectral_projectors(Hb)
            ents = []
            for i, ki in enumerate(ks):
                for j, kj in enumerate(ks):
                    lp = E.Laurent()
                    for lam, P in proj.items():
                        if not P[i][j].is_zero():
                            lp = lp + E.Laurent.mono((0, int(-4 * lam)), P[i][j])
                    if lp:
                        if kind == "step":
                            lp = lp.shift((-3 * nel[kj], 0) if order == 1 else (-3 * (nel[ki] + nel[kj]), 0))
                        ents.append((i, j, lp))
            blocks.append({"ks": list(ks), "entries": ents})
    al, be = 0.37, 0.61
    dA, dB = target_base(kind, order)
    Vf = enc.target(kind, al, be, order)
    Vd = np.zeros_like(Vf)
    for blk in blocks:
        for i, j, lp in blk["entries"]:
            Vd[blk["ks"][i], blk["ks"][j]] = lp.evaluate(al / dA, be / dB)
    err = float(np.abs(Vd - Vf).max())
    if err > _CERT_TOL:
        raise E.ExactError(f"exact {kind} target deviates from the float target by {err}")
    _EXACT_CACHE[key] = blocks
    return blocks


def laurent_target_matrix(enc, kind: str, alpha: float, beta: float, order: int = 1) -> np.ndarray:
    """Dense 433 x 433 evaluation of `exact_target_blocks` at (alpha, beta) (for the numerical self-check against
    `enc.target`)."""
    dA, dB = target_base(kind, order)
    V = np.zeros((len(enc.labels),) * 2, dtype=complex)
    for blk in exact_target_blocks(enc, kind, order):
        for i, j, lp in blk["entries"]:
            V[blk["ks"][i], blk["ks"][j]] = lp.evaluate(alpha / dA, beta / dB)
    return V


# ----- pins of the Lean checker (lean/Su2PlaqCert/SpinNet/Pins.lean)
def compute_pins(enc=None) -> dict:
    enc = enc or SpinNet()
    return {"states": PN.sha(PN.states_text(exact_states(enc))),
            "targets": {f"{kind}:{order}": PN.sha(PN.target_text(exact_target_blocks(enc, kind, order)))
                        for kind, order in SPIN_TARGETS}}


def render_pins_lean(p: dict) -> str:
    t = p["targets"]
    return f'''/-!
# Su2PlaqCert.SpinNet.Pins — fingerprints of the exporter's exact spin-network data (GENERATED by
`python -c "from su2plaq.spinnet.lean_export import write_pins; write_pins()"`; do not edit)

SHA-256 of the canonical text of the 433 exact physical states (unit vectors on the data|outer integer) and of the exact
route-B targets of U_E, U_B and the step (orders 1, 2) at their own base `(d_alpha, d_beta)`.  Same canonical text as
`Su2PlaqCert.Cert.statesText` / `targetText`; see `Su2PlaqCert.SpinNet.pinError`.
-/
namespace Su2PlaqCert.SpinNet.Pins

def statesSha256 : String := "{p["states"]}"

/-- `(d_alpha, d_beta)` of the exact targets. -/
def targetBase (kind : String) (order : Nat) : Option (Nat × Nat) :=
  match kind, order with
  | "UE", _ => some (4, 4)
  | "UB", _ => some (4, 4)
  | "step", 1 => some (4, 4)
  | "step", 2 => some (8, 4)
  | _, _ => none

def targetSha256 (kind : String) (order : Nat) : Option String :=
  match kind, order with
  | "UE", _ => some "{t["UE:1"]}"
  | "UB", _ => some "{t["UB:1"]}"
  | "step", 1 => some "{t["step:1"]}"
  | "step", 2 => some "{t["step:2"]}"
  | _, _ => none

end Su2PlaqCert.SpinNet.Pins
'''


def write_pins(path=None) -> pathlib.Path:
    path = pathlib.Path(path) if path is not None else SPIN_PINS_FILE
    path.write_text(render_pins_lean(compute_pins()))
    return path


# ----- export
def export_certificate(qc, enc, kind, alpha, beta, order, out_path, *, verdict_phases=None):
    """prompts/006 section 4 JSON certificate (schema su2plaq-cert-1) of `qc` against the exact route-B target (kind, order):
    gates via `sparse_sim._translate` (program order, angle exponents of the gate's own angle in units of
    alpha / d_alpha, beta / d_beta), states = the 433 unit codes (K-coefficient 1), target blocks = exact Laurent
    polynomials over K with base `target_base`, phase c = omega^j z_alpha^a z_beta^b fitted from the float simulation at
    three angle pairs.  Returns the path or an n_a reason string (`non_linear_angle:<gate>:<theta>`, `unitary_gate`,
    `phase_not_in_K`, `too_many_qubits`, ...).  `verdict_phases` (float evaluator phases at the nominal pair) are only
    cross-checked."""
    from su2plaq.encodings.base import ALT_ANGLES
    from su2plaq.evaluate import sparse_sim as ss

    t0 = time.time()
    n = qc.num_qubits
    if n > 62:
        return "too_many_qubits"
    if kind not in _PREFER:
        raise ValueError(f"unknown kind {kind!r}")
    try:
        layout = enc.layout_of(qc)
        perm = {q: i for i, q in enumerate(layout.data)}
        perm.update({q: N_DATA + j for j, q in enumerate(layout.outer)})
        perm.update({q: N_DATA + N_OUTER + k for k, q in enumerate(layout.ancilla)})
        if sorted(perm) != list(range(n)):
            raise ValueError("layout does not partition the circuit's qubits")
    except ValueError as exc:
        return f"bad_layout:{exc}"
    n_cert = N_DATA + N_OUTER + len(layout.ancilla)
    if n_cert > 62:
        return "too_many_qubits"
    try:
        ops, gphase = C._translate_export(qc)
    except ValueError as exc:
        return f"disallowed_gate:{exc}"
    t_base = target_base(kind, order)
    res = C._gate_records(ops, perm, alpha, beta, base_min=t_base, prefer=_PREFER[kind])
    if isinstance(res, str):
        return res
    recs, base, fr = res
    fa, fb = base[0] // t_base[0], base[1] // t_base[1]
    states = exact_states(enc)
    blocks = [{"ks": b["ks"], "entries": [(i, j, C._scale_laurent(lp, fa, fb)) for i, j, lp in b["entries"]]}
              for b in exact_target_blocks(enc, kind, order)]
    pairs = [(alpha, beta)] + [tuple(p) for p in ALT_ANGLES]
    diag = {}
    for b in blocks:
        for i, j, lp in b["entries"]:
            if i == j:
                diag[b["ks"][i]] = lp
    nom_mag = {k: abs(lp.evaluate(alpha / base[0], beta / base[1])) for k, lp in diag.items()}
    cand = [k for k in sorted(nom_mag, key=lambda k: -nom_mag[k]) if nom_mag[k] > 0.5][:3]
    if not cand:
        return "phase_not_in_K"
    ops_canon = [(nm, tuple(perm[q] for q in qs), pl) for nm, qs, pl in ops]
    cs, spread = [], 0.0
    try:
        for (al, be) in pairs:
            ops_f = []
            for (nm, qs, pl), r in zip(ops_canon, fr):
                ops_f.append((nm, qs, (float(r[0]) * al + float(r[1]) * be,)) if r is not None else (nm, qs, pl))
            c, sp_ = C._float_phase(ops_f, n_cert, states, diag, cand, (al, be), base)
            cs.append(c)
            spread = max(spread, sp_)
    except ss.SimCapExceeded:
        return "unsimulable"
    unit = all(abs(abs(c) - 1) < 1e-7 for c in cs) and spread < 1e-7
    fit = C._fit_phase([c / abs(c) for c in cs], pairs, base) if unit else None
    if fit is None:
        if unit:
            return "phase_not_in_K"
        fit = (0, 0, 0)          # the circuit is not the target up to a phase: let the exact checker reject it
    j_, a_, b_ = fit
    residual = None
    if verdict_phases:
        residual = float(abs(cs[0] / abs(cs[0]) * np.exp(1j * gphase) - verdict_phases[0]))
    gates_hash = hashlib.sha256(json.dumps(recs).encode()).hexdigest()
    cert = {
        "schema": "su2plaq-cert-1", "circuit_id": f"spinnet-{kind}-o{order}-{gates_hash[:12]}", "program_sha256": gates_hash,
        "n_qubits": n_cert, "n_data": N_DATA, "n_outer": N_OUTER, "base": {"d_alpha": base[0], "d_beta": base[1]},
        "gates": recs,
        "states": [{"k": k, "label": str(enc.labels[k]),
                    "terms": [{"code": int(c), "c": a.to_json()} for c, a in zip(st["codes"], st["amps"])]}
                   for k, st in enumerate(states)],
        "target": {"kind": kind, "order": order,
                   "blocks": [{"ks": b["ks"], "entries": [[i, j, lp.to_json()] for i, j, lp in b["entries"]]}
                              for b in blocks]},
        "phase": {"k": E.omega_power(j_).to_json(), "m": [a_, b_]},
        "provenance": {"git_commit": C._git_commit(), "encoding": enc.name, "alpha_nominal": alpha, "beta_nominal": beta,
                       "float_phase_spread": spread, "float_phase_cross_check": residual,
                       "exporter": "su2plaq.spinnet.lean_export", "export_seconds": time.time() - t0},
    }
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert, separators=(",", ":")))
    return out_path


# ----- check
def checker_exe() -> pathlib.Path:
    """Compiled spin-network checker; `lake build su2plaq_cert_spinnet` (a no-op when up to date) once per process."""
    global _BUILT
    exe = project.LEAN_DIR / ".lake" / "build" / "bin" / CHECKER_TARGET
    if not _BUILT or not exe.exists():
        r = project.build(CHECKER_TARGET, timeout=1800)
        if not r["ok"]:
            raise RuntimeError("cannot build the spin-network Lean checker:\n" + r["stderr"][-2000:] + r["stdout"][-2000:])
        _BUILT = True
    return exe


def check_certificate(path, timeout: float = 900.0) -> dict:
    """`su2plaq_cert_spinnet check <path>`: ACCEPT -> certified, REJECT <reason> -> rejected, anything else -> failed."""
    t0 = time.time()
    try:
        exe = checker_exe()
        sha = hashlib.sha256(exe.read_bytes()).hexdigest()
        r = subprocess.run([str(exe), "check", str(path)], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "reason": f"timeout after {timeout}s", "seconds": time.time() - t0, "checker_sha256": ""}
    except (RuntimeError, OSError) as exc:
        return {"status": "failed", "reason": str(exc), "seconds": time.time() - t0, "checker_sha256": ""}
    line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    dt = time.time() - t0
    if line == "ACCEPT":
        return {"status": "certified", "reason": "", "seconds": dt, "checker_sha256": sha}
    if line.startswith("REJECT"):
        return {"status": "rejected", "reason": line[len("REJECT"):].strip(), "seconds": dt, "checker_sha256": sha}
    return {"status": "failed", "reason": f"checker output {line!r} stderr {r.stderr.strip()[-300:]!r}", "seconds": dt,
            "checker_sha256": sha}


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0) -> dict:
    """Export + check: {"status": "certified"|"rejected"|"n_a"|"failed", "reason", "cert_path", "seconds", "axioms": [],
    "check_seconds", "checker_sha256"}.  The checker is a compiled executable (computable Lean code, no kernel axiom is
    involved: `axioms` is empty); `n_a` carries the exporter's reason (angles that are not rational multiples of
    alpha / beta, unitary gates, ...).  Certificates go to results/spinnet/certs/<circuit_id>.json by default."""
    t0 = time.time()
    out_dir = pathlib.Path(out_dir) if out_dir is not None else CERT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f"spinnet-{kind}-o{order}-pending-{os.getpid()}-{abs(hash(id(qc))) % 10**8}.json"
    try:
        res = export_certificate(qc, enc, kind, alpha, beta, order, tmp)
    except E.ExactError as exc:
        return {"status": "failed", "reason": f"exact export failed: {exc}", "cert_path": None,
                "seconds": time.time() - t0, "axioms": []}
    if isinstance(res, str):
        return {"status": "n_a", "reason": res, "cert_path": None, "seconds": time.time() - t0, "axioms": []}
    final = out_dir / (json.loads(res.read_text())["circuit_id"] + ".json")
    res.replace(final)
    out = check_certificate(final, timeout=timeout)
    return {"status": out["status"], "reason": out["reason"], "cert_path": str(final), "seconds": time.time() - t0,
            "axioms": [], "check_seconds": out["seconds"], "checker_sha256": out["checker_sha256"]}


# ----- theorem file (step 4.L1)
def _exporter_mismatch(path, enc=None) -> str | None:
    """Compare the trusted inputs of a spin-network certificate -- the 433 states and the target blocks -- with the exact data
    of this exporter entry by entry (the Lean checker re-verifies both through the SHA-256 pins; this refuses early and for the
    theorem-file writer).  Returns a reason or None."""
    enc = enc or SpinNet()
    try:
        d = json.loads(pathlib.Path(path).read_text())
        if not isinstance(d, dict) or d.get("schema") != "su2plaq-cert-1":
            return "not a su2plaq-cert-1 certificate"
        if d.get("n_data") != N_DATA or d.get("n_outer") != N_OUTER or "states" not in d or "target" not in d:
            return "not a spin-network certificate (n_data 8, n_outer 8, states, target)"
        exp = exact_states(enc)
        if len(d["states"]) != len(exp):
            return f"certificate has {len(d['states'])} states, the physical basis has {len(exp)}"
        seen = set()
        for st in d["states"]:
            k = st["k"]
            if k in seen or not 0 <= k < len(exp):
                return f"bad or duplicate state index {k}"
            seen.add(k)
            want = {int(c): a for c, a in zip(exp[k]["codes"], exp[k]["amps"])}
            have = {int(t["code"]): E.KNum.from_json(t["c"]) for t in st["terms"]}
            if len(have) != len(st["terms"]) or have != want:
                return f"state {k} differs from the exact physical basis"
        tgt = d["target"]
        kind, order = tgt["kind"], int(tgt.get("order", 1))
        if (kind, order if kind == "step" else 1) not in SPIN_TARGETS:
            return f"unknown target kind {kind!r} order {order}"
        t_base = target_base(kind, order)
        fa, fb = d["base"]["d_alpha"] // t_base[0], d["base"]["d_beta"] // t_base[1]
        if d["base"]["d_alpha"] != fa * t_base[0] or d["base"]["d_beta"] != fb * t_base[1] or fa < 1 or fb < 1:
            return "base is not a positive multiple of the target's base"
        blocks = [{"ks": b["ks"], "entries": [[i, j, C._scale_laurent(lp, fa, fb).to_json()] for i, j, lp in b["entries"]]}
                  for b in exact_target_blocks(enc, kind, order)]
        got = [{"ks": b["ks"], "entries": [[i, j, lp] for i, j, lp in b["entries"]]} for b in tgt["blocks"]]
        if json.dumps(got, sort_keys=True) != json.dumps(blocks, sort_keys=True):
            return f"target blocks differ from the exact {kind} target"
    except (KeyError, TypeError, ValueError, E.ExactError) as exc:
        return f"malformed certificate: {type(exc).__name__}: {exc}"
    return None


def write_theorem_file(cert_path, theorem_name: str, out_path, comment: str | None = None) -> pathlib.Path:
    """Write `import Su2PlaqCert.SpinNet.Check` + the certificate JSON as a Lean string literal + `theorem <name> :
    Su2PlaqCert.SpinNet.checkJsonString certJson = true := by native_decide` + `#print axioms <name>` (standard axioms plus one
    per-theorem `native_decide` axiom: compiler trust).  Elaborate with `cd lean && lake env lean <out_path>`.  The pattern of
    `su2plaq.lean.certify.write_theorem_file`; refuses a certificate whose states / target differ from this exporter's exact data.
    `comment` (optional) becomes a first line `-- <comment>`."""
    cert_path, out_path = pathlib.Path(cert_path), pathlib.Path(out_path)
    why = _exporter_mismatch(cert_path)
    if why is not None:
        raise ValueError(f"refusing to write a theorem file for a certificate that differs from the exporter's exact data: {why}")
    text = cert_path.read_text()
    d = json.loads(text)
    if not theorem_name.replace("_", "").isalnum() or len(theorem_name) > 13:
        # `#print axioms` prints one line only if the whole message fits in 120 columns: 92 + 2 * len(name)
        raise ValueError(f"bad theorem name {theorem_name!r} (alphanumeric/underscore, at most 13 characters)")
    lit = text.replace("\\", "\\\\").replace('"', '\\"')
    if "\n" in lit or "\r" in lit:
        raise ValueError("certificate JSON must be a single line")
    if comment is not None and ("\n" in comment or "\r" in comment):
        raise ValueError("comment must be a single line")
    prov = d.get("provenance", {})
    first = f"-- {comment}\n" if comment else ""
    head = (
        first +
        "import Su2PlaqCert.SpinNet.Check\n\n"
        "/-! Generated by `su2plaq.spinnet.lean_export.write_theorem_file` -- do not edit.\n"
        f"circuit_id {d.get('circuit_id')}; git {prov.get('git_commit')}; exporter {prov.get('exporter')};\n"
        f"certificate sha256 {hashlib.sha256(text.encode()).hexdigest()}; {len(d['gates'])} gates, {d['n_qubits']} qubits.\n"
        "`native_decide` runs the compiled checker `Su2PlaqCert.SpinNet.checkJsonString` (trust: Lean compiler + checker source). -/\n\n")
    body = (f'def certJson : String := "{lit}"\n\n'
            f"theorem {theorem_name} : Su2PlaqCert.SpinNet.checkJsonString certJson = true := by native_decide\n\n"
            f"#print axioms {theorem_name}\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(head + body)
    return out_path
