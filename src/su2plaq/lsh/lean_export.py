"""Lean tables and native certificate export for the LSH encoding (prompts/400 section 2; docs/METHODS-lsh.md L10).
Step 7.L2: the integer tables and the circuit model of lean/Su2Plaq/LSH/Circuit.lean (`coupling_ints`, `partner_ints`,
`angle_ints`, `lean_literals`, `write_lean_tables`).  Step 7.L3: the native per-circuit certificate (schema su2plaq-cert-1,
prompts/006 section 4) of an LSH circuit against the exact LSH / route-B target, checked by the compiled Lean executable
`su2plaq_cert_lsh` (lean/Su2PlaqCert/LSH/, which reuses the laptop's replay/compare code read-only and pins its own 433
unit-code states and targets).  Adapted from `su2plaq.spinnet.lean_export` (register sizes 12 + 12, LSH electric weight)."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import time
from fractions import Fraction

import numpy as np

from su2plaq.lean import certify as C
from su2plaq.lean import exact as E
from su2plaq.lean import pins as PN
from su2plaq.lean import project
from su2plaq.lsh import operators as O
from su2plaq.lsh import walk as W

ROOT = pathlib.Path(__file__).resolve().parents[3]
CIRCUIT_LEAN = ROOT / "lean" / "Su2Plaq" / "LSH" / "Circuit.lean"
_BEGIN = "-- BEGIN generated"
_END = "-- END generated"
_N_TRANS, _N_FRAME = len(W.TRANSCODE), len(W.FRAME)


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


# ----- native certificate (step 7.L3)
CERT_DIR = ROOT / "results" / "lsh" / "certs"
LSH_PINS_FILE = ROOT / "lean" / "Su2PlaqCert" / "LSH" / "Pins.lean"
CHECKER_TARGET = "su2plaq_cert_lsh"
N_DATA, N_OUTER = 12, 12              # canonical frame: data i -> i, outer j -> 12 + j, ancilla k -> 24 + k (= the circuit's own)
LSH_TARGETS = (("UE", 1), ("UB", 1), ("step", 1), ("step", 2))
_CERT_TOL = 1e-12
_PREFER = {"UE": "a", "UB": "b", "step": "ab"}
_EXACT_CACHE: dict = {}
_BUILT = False
# provenance fields that change on every export without changing what the certificate says (audit 303 N2, prompts/401 8.A2):
# `certify` keeps an existing certificate that differs from a fresh export only in these.
VOLATILE_PROVENANCE = ("git_commit", "git_dirty", "export_seconds")
_FLOAT_PROVENANCE = ("float_phase_spread", "float_phase_cross_check")   # float simulation residuals, equal up to rounding


def target_base(kind: str, order: int = 1) -> tuple:
    """(d_alpha, d_beta): theta_alpha = alpha / d_alpha, theta_beta = beta / d_beta of `exact_target_blocks`
    (z_beta = exp(i beta / 4) makes every eigenvalue lambda in {0, +-1/2, +-1, +-2} of H_B an integer exponent -4 lambda)."""
    return (8 if (kind == "step" and order == 2) else 4, 4)


def exact_states(enc) -> list:
    """The 433 physical states as exact K-vectors in the form of `su2plaq.lean.exact.exact_encoded_states`: unit vectors
    [{"codes": int64[1], "amps": [K(1)]}] indexed by the label index k."""
    return [{"codes": np.array([int(c[0])], dtype=np.int64), "amps": [E.K_ONE]} for c in enc.physical_vectors().codes]


def _exact_hb(enc) -> dict:
    """{(i, j): K} nonzero entries of H_B^phys (433 x 433): couplings are recognised as rationals of denominator <= 2 within
    1e-12 (they are -2, -1/2, 1), raising otherwise; the matrix must be real symmetric."""
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
    """sum_c N_n(c) = number of inner links with j = 1/2 for every state k, read from the n-leg flux of the four 'in' sites;
    cross-checked against the float H_E (3/4 per spin-1/2 inner link)."""
    codes = [int(c[0]) for c in enc.physical_vectors().codes]
    nel = [sum(O.site_flux((c >> (3 * k)) & 7)[1] for k in range(4)) for c in codes]
    err = float(np.abs(enc.h_electric() - 0.75 * np.array(nel)).max())
    if err > _CERT_TOL:
        raise E.ExactError(f"inner electric energy differs from 3/4 x #(j=1/2 inner links) by {err}")
    return nel


def exact_target_blocks(enc, kind: str, order: int = 1) -> list:
    """Exact target in blocks [{"ks": [...], "entries": [(i, j, Laurent)]}], V[ks[i], ks[j]] a Laurent polynomial in
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


# ----- pins of the Lean checker (lean/Su2PlaqCert/LSH/Pins.lean)
def compute_pins(enc=None) -> dict:
    if enc is None:
        from su2plaq.encodings.lsh import LSH
        enc = LSH()
    return {"states": PN.sha(PN.states_text(exact_states(enc))),
            "targets": {f"{kind}:{order}": PN.sha(PN.target_text(exact_target_blocks(enc, kind, order)))
                        for kind, order in LSH_TARGETS}}


def render_pins_lean(p: dict) -> str:
    t = p["targets"]
    return f'''/-!
# Su2PlaqCert.LSH.Pins — fingerprints of the exporter's exact LSH data (GENERATED by
`python -c "from su2plaq.lsh.lean_export import write_pins; write_pins()"`; do not edit)

SHA-256 of the canonical text of the 433 exact physical states (unit vectors on the data|outer integer, 12 + 12 qubits) and of
the exact LSH / route-B targets of U_E, U_B and the step (orders 1, 2) at their own base `(d_alpha, d_beta)`.  Same canonical
text as `Su2PlaqCert.Cert.statesText` / `targetText`; see `Su2PlaqCert.LSH.pinError`.
-/
namespace Su2PlaqCert.LSH.Pins

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

end Su2PlaqCert.LSH.Pins
'''


def write_pins(path=None) -> pathlib.Path:
    """Write lean/Su2PlaqCert/LSH/Pins.lean (or `path`) from the exporter's exact states and targets."""
    path = pathlib.Path(path) if path is not None else LSH_PINS_FILE
    path.write_text(render_pins_lean(compute_pins()))
    return path


# ----- export
def _git_dirty() -> bool | None:
    """Uncommitted changes to tracked files (as `su2plaq.metrics.provenance`); None outside a repository."""
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(r.stdout.strip()) if r.returncode == 0 else None


def export_certificate(qc, enc, kind, alpha, beta, order, out_path, *, verdict_phases=None, extra_provenance: dict | None = None):
    """prompts/006 section 4 JSON certificate (schema su2plaq-cert-1) of `qc` against the exact LSH target (kind, order):
    gates via `sparse_sim._translate` (program order, angle exponents of the gate's own angle in units of
    alpha / d_alpha, beta / d_beta), states = the 433 unit codes (K-coefficient 1), target blocks = exact Laurent
    polynomials over K with base `target_base`, phase c = omega^j z_alpha^a z_beta^b fitted from the float simulation at
    three angle pairs.  Returns the path or an n_a reason string (`non_linear_angle:<gate>:<theta>`, `unitary_gate`,
    `phase_not_in_K`, `too_many_qubits`, ...).  `verdict_phases` (float evaluator phases at the nominal pair) are only
    cross-checked.  `extra_provenance` (e.g. `{"entry_id": ..., "program_file_sha256": ...}`) is merged into the certificate's
    `provenance` block (binding fields); the certificate also records `git_dirty` and `gates_sha256` (the gate-list hash,
    alias of `program_sha256`)."""
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
        "schema": "su2plaq-cert-1", "circuit_id": f"lsh-{kind}-o{order}-{gates_hash[:12]}", "gates_sha256": gates_hash,
        "program_sha256": gates_hash,
        "n_qubits": n_cert, "n_data": N_DATA, "n_outer": N_OUTER, "base": {"d_alpha": base[0], "d_beta": base[1]},
        "gates": recs,
        "states": [{"k": k, "label": str(enc.labels[k]),
                    "terms": [{"code": int(c), "c": a.to_json()} for c, a in zip(st["codes"], st["amps"])]}
                   for k, st in enumerate(states)],
        "target": {"kind": kind, "order": order,
                   "blocks": [{"ks": b["ks"], "entries": [[i, j, lp.to_json()] for i, j, lp in b["entries"]]}
                              for b in blocks]},
        "phase": {"k": E.omega_power(j_).to_json(), "m": [a_, b_]},
        "provenance": {"git_commit": C._git_commit(), "git_dirty": _git_dirty(), "encoding": enc.name, "alpha_nominal": alpha, "beta_nominal": beta,
                       "float_phase_spread": spread, "float_phase_cross_check": residual,
                       "exporter": "su2plaq.lsh.lean_export", "export_seconds": time.time() - t0, **(extra_provenance or {})},
    }
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert, separators=(",", ":")))
    return out_path


# ----- check
def checker_exe() -> pathlib.Path:
    """Compiled LSH checker; `lake build su2plaq_cert_lsh` (a no-op when up to date) once per process."""
    global _BUILT
    exe = project.LEAN_DIR / ".lake" / "build" / "bin" / CHECKER_TARGET
    if not _BUILT or not exe.exists():
        r = project.build(CHECKER_TARGET, timeout=1800)
        if not r["ok"]:
            raise RuntimeError("cannot build the LSH Lean checker:\n" + r["stderr"][-2000:] + r["stdout"][-2000:])
        _BUILT = True
    return exe


def check_certificate(path, timeout: float = 900.0) -> dict:
    """`su2plaq_cert_lsh check <path>`: ACCEPT -> certified, REJECT <reason> -> rejected, anything else -> failed."""
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


def _same_up_to_volatile(a: dict, b: dict) -> bool:
    """True iff two certificates are equal after dropping VOLATILE_PROVENANCE (and comparing the float-simulation residuals
    of the provenance block up to 1e-9)."""
    a, b = json.loads(json.dumps(a)), json.loads(json.dumps(b))
    pa, pb = a.get("provenance", {}), b.get("provenance", {})
    for k in VOLATILE_PROVENANCE:
        pa.pop(k, None)
        pb.pop(k, None)
    for k in _FLOAT_PROVENANCE:
        x, y = pa.pop(k, None), pb.pop(k, None)
        if (x is None) != (y is None) or (x is not None and abs(float(x) - float(y)) > 1e-9):
            return False
    return a == b


def certify(qc, enc, kind, alpha, beta, order, out_dir=None, timeout: float = 900.0, extra_provenance: dict | None = None) -> dict:
    """Export + check: {"status": "certified"|"rejected"|"n_a"|"failed", "reason", "cert_path", "seconds", "axioms": [],
    "check_seconds", "checker_sha256"}.  The checker is a compiled executable (computable Lean code, no kernel axiom is
    involved: `axioms` is empty); `n_a` carries the exporter's reason (angles that are not rational multiples of
    alpha / beta, unitary gates, ...).  Certificates go to results/lsh/certs/<circuit_id>.json by default.
    `extra_provenance` is written inside the certificate (binding fields).  An existing certificate of the same name that
    differs from the fresh export only in VOLATILE_PROVENANCE is left untouched (no rewrite, no dirty tree); a changed
    binding or content replaces it.  The temporary file never outlives the call."""
    t0 = time.time()
    out_dir = pathlib.Path(out_dir) if out_dir is not None else CERT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f"lsh-{kind}-o{order}-pending-{os.getpid()}-{abs(hash(id(qc))) % 10**8}.json"
    try:
        try:
            res = export_certificate(qc, enc, kind, alpha, beta, order, tmp, extra_provenance=extra_provenance)
        except E.ExactError as exc:
            return {"status": "failed", "reason": f"exact export failed: {exc}", "cert_path": None,
                    "seconds": time.time() - t0, "axioms": []}
        if isinstance(res, str):
            return {"status": "n_a", "reason": res, "cert_path": None, "seconds": time.time() - t0, "axioms": []}
        fresh = json.loads(res.read_text())
        final = out_dir / (fresh["circuit_id"] + ".json")
        keep = False
        if final.exists():
            try:
                keep = _same_up_to_volatile(json.loads(final.read_text()), fresh)
            except (OSError, ValueError):
                keep = False
        if keep:
            res.unlink()
        else:
            res.replace(final)
    finally:
        if tmp.exists():
            tmp.unlink()
    out = check_certificate(final, timeout=timeout)
    return {"status": out["status"], "reason": out["reason"], "cert_path": str(final), "seconds": time.time() - t0,
            "axioms": [], "check_seconds": out["seconds"], "checker_sha256": out["checker_sha256"]}


# ----- theorem file (step 8.L)
def _exporter_mismatch(path, enc=None) -> str | None:
    """Compare the trusted inputs of an LSH certificate -- the 433 states and the target blocks -- with the exact data of
    this exporter entry by entry (the Lean checker re-verifies both through the SHA-256 pins; this refuses early and for the
    theorem-file writer).  Returns a reason or None."""
    if enc is None:
        from su2plaq.encodings.lsh import LSH
        enc = LSH()
    try:
        d = json.loads(pathlib.Path(path).read_text())
        if not isinstance(d, dict) or d.get("schema") != "su2plaq-cert-1":
            return "not a su2plaq-cert-1 certificate"
        if d.get("n_data") != N_DATA or d.get("n_outer") != N_OUTER or "states" not in d or "target" not in d:
            return "not an LSH certificate (n_data 12, n_outer 12, states, target)"
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
        if (kind, order if kind == "step" else 1) not in LSH_TARGETS:
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
    """Write `import Su2PlaqCert.LSH.Check` + the certificate JSON as a Lean string literal + `theorem <name> :
    Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide` + `#print axioms <name>` (standard axioms plus one
    per-theorem `native_decide` axiom: compiler trust).  Elaborate with `cd lean && lake env lean <out_path>`.  As
    `su2plaq.spinnet.lean_export.write_theorem_file`; refuses (ValueError) a certificate whose states / target differ from
    this exporter's exact LSH data.  `comment` (optional) becomes a first line `-- <comment>`."""
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
        "import Su2PlaqCert.LSH.Check\n\n"
        "/-! Generated by `su2plaq.lsh.lean_export.write_theorem_file` -- do not edit.\n"
        f"circuit_id {d.get('circuit_id')}; git {prov.get('git_commit')}; exporter {prov.get('exporter')};\n"
        f"certificate sha256 {hashlib.sha256(text.encode()).hexdigest()}; {len(d['gates'])} gates, {d['n_qubits']} qubits.\n"
        "`native_decide` runs the compiled checker `Su2PlaqCert.LSH.checkJsonString` (trust: Lean compiler + checker source). -/\n\n")
    body = (f'def certJson : String := "{lit}"\n\n'
            f"theorem {theorem_name} : Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide\n\n"
            f"#print axioms {theorem_name}\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(head + body)
    return out_path
