"""Three-angle Laurent certificates for rishon circuits (prompts/203 section 3.2, steps 6.L2-6.L4; prompts/204 section 6.4).

A circuit is certified by the exact checker `su2plaq_rishon_cert` (`lean/Su2PlaqCert/Rishon/`, Mathlib-free): for each of the 1296
inner codes the gate list is replayed on the basis state `|code>` with exact coefficients in Laurent polynomials over
`K = Q(i, sqrt2, sqrt3)` in the three unit-circle variables `z_alpha = e^{i alpha/d_alpha}`, `z_beta = e^{i beta/d_beta}`,
`z_gamma = e^{i sqrt2 beta/d_gamma}`, and compared with the exact target column times one global phase `k z^m`.  An identity of
Laurent polynomials holds for every real angle triple, so one certificate covers all `(alpha, beta)`.

Conventions of the certificate JSON (schema `SCHEMA`): little-endian qubits, data qubit `i -> i`, ancilla `k -> 16 + k`; the 32 outer
qubits must be untouched and are dropped (`outer_dropped`).  A gate angle is `(m_alpha theta_alpha + m_beta theta_beta + m_gamma
theta_gamma)` (`rz` uses the half angle, so its exponents are even by construction of the base).  `states` is the list of the 1296 inner
codes (the checker regenerates it), `target.entries` the sparse exact target `[[i, j, laurent3]]` at the certificate base, `phase` the
fitted global phase.  The det layer is certified with the same schema and checker, `eta` in the first formal slot
(`certify_det_layer`; `provenance.angle_slots = {"alpha": "eta"}`).

Lean never changes validity: a failure is a status, not an exception.  Statuses: certified | rejected | n_a | failed.
CLI: `python -m su2plaq.rishon.lean_cert pins` regenerates `lean/Su2PlaqCert/Rishon/Pins3.lean`.
"""
from __future__ import annotations

import functools
import hashlib
import itertools
import json
import math
import pathlib
import re
import subprocess
import sys
import time
from fractions import Fraction

import numpy as np

from su2plaq.lean import certify as C
from su2plaq.lean import exact as E
from su2plaq.lean import project as P
from su2plaq.lean.certify import LeanCert

SCHEMA = "su2plaq-rishon-cert3-1"
_SQRT2 = math.sqrt(2.0)
N_DATA, N_OUTER, N_INNER = 16, 32, 1296
PINS_FILE = P.LEAN_DIR / "Su2PlaqCert" / "Rishon" / "Pins3.lean"
CROSS_TOL = 1e-12                       # exact target vs the float `operators.inner_target` at the nominal angles
FIT_TOL = 1e-7                          # float phase fit
LINEAR_TOL = 1e-9                       # as `robust.LINEAR_TOL`
_KINDS = ("UE", "UB", "UD", "step")


# --------------------------------------------------------------------------------------------------------------------
class Laurent3(dict):
    """Laurent polynomial in (z_alpha, z_beta, z_gamma) over K: dict[(m_alpha, m_beta, m_gamma)] -> KNum (no zero coefficients)."""

    @staticmethod
    def mono(exp, k) -> "Laurent3":
        out = Laurent3()
        k = E.KNum.of(k)
        if not k.is_zero():
            out[(int(exp[0]), int(exp[1]), int(exp[2]))] = k
        return out

    def __add__(self, other: "Laurent3") -> "Laurent3":
        out = Laurent3(self)
        for e, k in other.items():
            s = out[e] + k if e in out else k
            if s.is_zero():
                out.pop(e, None)
            else:
                out[e] = s
        return out

    def scale(self, k) -> "Laurent3":
        k = E.KNum.of(k)
        if k.is_zero():
            return Laurent3()
        return Laurent3({e: v * k for e, v in self.items()})

    def shift(self, exp) -> "Laurent3":
        return Laurent3({(e[0] + exp[0], e[1] + exp[1], e[2] + exp[2]): v for e, v in self.items()})

    def __mul__(self, other) -> "Laurent3":
        if not isinstance(other, Laurent3):
            return self.scale(E.KNum.of(other))
        out = Laurent3()
        for e2, k2 in other.items():
            out = out + self.shift(e2).scale(k2)
        return out

    def evaluate(self, theta_alpha: float, theta_beta: float, theta_gamma: float) -> complex:
        tot = 0j
        for (ma, mb, mg), k in self.items():
            tot += k.to_complex() * np.exp(1j * (ma * theta_alpha + mb * theta_beta + mg * theta_gamma))
        return complex(tot)

    def to_json(self) -> list:
        return [[list(e), k.to_json()] for e, k in sorted(self.items())]

    @staticmethod
    def from_json(lst) -> "Laurent3":
        out = Laurent3()
        for e, k in lst:
            out = out + Laurent3.mono((int(e[0]), int(e[1]), int(e[2])), E.KNum.from_json(k))
        return out


# --------------------------------------------------------------------------------------------------------------------
# angle recognition
def recognise_angle(theta: float, alpha: float, beta: float, max_den: int = 64, tol: float = 1e-12):
    """(m_alpha, m_beta, m_gamma, d) with theta = (m_alpha alpha + m_beta beta + m_gamma sqrt2 beta)/d (the three-variable rule of
    prompts/203 section 2), d the smallest positive integer <= max_den that admits integer m (so gcd(m, d) = 1), |m| <= 64 d
    (|m| <= 128 when all of alpha, beta and sqrt2 beta are used); None if there is none.  Pure Python (no Lean).

    Search order: smallest d first; for each d the supports (a) alpha alone, (b) beta and sqrt2 beta (1 and sqrt2 are
    independent over Q, so the pair is unique), (c) alpha together with a nonzero sqrt2 beta part.  Inside a support the
    smallest sum |m| wins.  A combination of alpha and beta WITHOUT sqrt2 beta is deliberately not recognised: alpha and beta
    are both rational at the nominal pair (0.37, 0.61), so such a combination fits every decimal angle (0.123 =
    (5 alpha + beta)/20) and carries no information.  Angle 0 is (0, 0, 0, 1).  `tol` bounds |fit - theta| in radians."""
    theta, alpha, beta = float(theta), float(alpha), float(beta)
    if alpha <= 0.0 or beta <= 0.0 or max_den < 1:
        raise ValueError("recognise_angle needs alpha > 0, beta > 0 and max_den >= 1")
    gam = _SQRT2 * beta
    if abs(theta) <= tol:
        return (0, 0, 0, 1)
    for d in range(1, int(max_den) + 1):
        target, eps, bound = theta * d, tol * d, 64 * d
        m = int(np.rint(target / alpha))              # (a) alpha alone
        if m != 0 and abs(m) <= bound and abs(m * alpha - target) <= eps:
            return (m, 0, 0, d)
        mg = np.arange(-bound, bound + 1, dtype=np.int64)    # (b) beta and sqrt2 beta
        mb = np.rint((target - mg * gam) / beta)
        ok = (np.abs(mb * beta + mg * gam - target) <= eps) & (np.abs(mb) <= bound)
        if ok.any():
            cost = np.where(ok, np.abs(mb) + np.abs(mg), np.inf)
            i = int(np.argmin(cost))
            return (0, int(mb[i]), int(mg[i]), d)
        b3 = min(bound, 128)                          # (c) alpha with a nonzero sqrt2 beta part
        ma = np.arange(-b3, b3 + 1, dtype=np.int64)
        mgc = np.arange(-b3, b3 + 1, dtype=np.int64)
        MA, MG = np.meshgrid(ma, mgc, indexing="ij")
        MB = np.rint((target - MA * alpha - MG * gam) / beta)
        ok = (np.abs(MB * beta + MA * alpha + MG * gam - target) <= eps) & (np.abs(MB) <= b3) & (MA != 0) & (MG != 0)
        if ok.any():
            cost = np.where(ok, np.abs(MA) + np.abs(MB) + np.abs(MG), np.inf)
            i, j = np.unravel_index(int(np.argmin(cost)), cost.shape)
            return (int(MA[i, j]), int(MB[i, j]), int(MG[i, j]), d)
    return None


def recognise_angle_single(theta: float, base: float, max_den: int = 64, tol: float = 1e-12):
    """(m, d) with theta = m base / d, d the smallest positive integer <= max_den (so gcd(m, d) = 1) and |m| <= 64 d; None if there is
    none.  Angle 0 is (0, 1).  The one-variable rule of the det layer (eta in the first formal slot, prompts/204 section 6.4)."""
    theta, base = float(theta), float(base)
    if base <= 0.0 or max_den < 1:
        raise ValueError("recognise_angle_single needs base > 0 and max_den >= 1")
    if abs(theta) <= tol:
        return (0, 1)
    r = Fraction(theta / base).limit_denominator(int(max_den))
    if abs(theta - float(r) * base) <= tol * r.denominator and abs(r.numerator) <= 64 * r.denominator:
        return (int(r.numerator), int(r.denominator))
    return None


# --------------------------------------------------------------------------------------------------------------------
# exact targets
_SECTOR_Q = (5, 6, 9, 10)
_SECTOR = (3, 5, 6, 9, 10, 12)


@functools.lru_cache(maxsize=None)
def _exact_amp(x: float) -> "E.KNum":
    """Exact K element of a pair-vector amplitude (recognised on a lattice, then checked to 1e-12)."""
    k = E.KNum.recognise(complex(x), 1e-12)
    if k is None or abs(k.to_complex() - x) > 1e-12:
        raise E.ExactError(f"amplitude {x!r} is not an element of K (denominator <= 48)")
    return k


def _amp(x: float) -> "E.KNum":
    return _exact_amp(round(float(x), 13))


def _half() -> "E.KNum":
    return E.KNum(Fraction(1, 2))


def _n_quartet(codes: np.ndarray) -> np.ndarray:
    q = np.zeros(len(codes), dtype=np.int64)
    for l in range(4):
        q += np.isin((codes >> (4 * l)) & 15, _SECTOR_Q)
    return q


def _kappa_slot(kappa: float) -> tuple:
    """Exponent triple of z with z^1 = e^{i kappa beta}: (0, n, 0) for kappa = n integer, (0, 0, n) for kappa = n sqrt2."""
    n = round(kappa)
    if abs(kappa - n) <= 1e-9:
        return (0, int(n), 0)
    n = round(kappa / _SQRT2)
    if abs(kappa - n * _SQRT2) <= 1e-9:
        return (0, 0, int(n))
    raise E.ExactError(f"bright-pair coupling kappa = {kappa!r} is not an integer multiple of 1 or sqrt2")


@functools.lru_cache(maxsize=1)
def _ub_entries() -> dict:
    """exp(-i beta H_B^in) = 1 + sum_p [(cos k b - 1)(|u><u| + |v><v|) + i sin(k b)(|u><v| + |v><u|)] with
    cos = (z + 1/z)/2, i sin = (z - 1/z)/2 (z = z_beta^n or z_gamma^n, n from kappa)."""
    from su2plaq.rishon import operators as O

    half = _half()
    ents: dict = {}
    for u, v, kappa in O.bright_pairs():
        e = _kappa_slot(kappa)
        neg = tuple(-x for x in e)
        cm1 = Laurent3.mono(e, half) + Laurent3.mono(neg, half) + Laurent3.mono((0, 0, 0), E.KNum(-1))
        isn = Laurent3.mono(e, half) + Laurent3.mono(neg, -half)
        sup = [int(i) for i in np.flatnonzero((np.abs(u) > 1e-13) | (np.abs(v) > 1e-13))]
        ua = {i: _amp(u[i]) for i in sup}
        va = {i: _amp(v[i]) for i in sup}
        for i in sup:
            for j in sup:
                a = ua[i] * ua[j] + va[i] * va[j]
                b = ua[i] * va[j] + va[i] * ua[j]
                lp = cm1.scale(a) + isn.scale(b)
                if lp:
                    ents[(i, j)] = ents[(i, j)] + lp if (i, j) in ents else lp
    for i in range(N_INNER):
        one = Laurent3.mono((0, 0, 0), E.K_ONE)
        ents[(i, i)] = ents[(i, i)] + one if (i, i) in ents else one
        if not ents[(i, i)]:
            del ents[(i, i)]
    return ents


def _ue_phase_exps(num: int, den: int) -> np.ndarray:
    """Exponent of z_alpha (unit alpha/den) of U_E(alpha) on each inner code: -num * #Q (electric coefficient num/den)."""
    from su2plaq.rishon import operators as O

    return -num * _n_quartet(O.inner_codes())


def _electric_fraction() -> Fraction:
    from su2plaq.rishon import operators as O

    c = float(O.electric_coefficient())
    f = Fraction(c).limit_denominator(64)
    if abs(float(f) - c) > 1e-13:
        raise E.ExactError(f"electric coefficient {c!r} is not a small rational")
    return f


def _ud_entries() -> dict:
    """exp(-i eta H_D^in) = tensor over the four links of the 6 x 6 layer 1 + (c - 1)(|A><A| + |B><B|) - i s (|A><B| + |B><A|),
    c = cos 2 eta = (z^2 + z^-2)/2, -i s = (z^-2 - z^2)/2, z = z_alpha (the slot of eta), A = code 3, B = code 12 (sector index 0, 5)."""
    half = _half()
    diag = Laurent3.mono((2, 0, 0), half) + Laurent3.mono((-2, 0, 0), half)
    off = Laurent3.mono((-2, 0, 0), half) + Laurent3.mono((2, 0, 0), -half)
    one = Laurent3.mono((0, 0, 0), E.K_ONE)
    layer: dict = {}
    for s in range(6):
        layer[(s, s)] = diag if s in (0, 5) else one
    layer[(0, 5)] = off
    layer[(5, 0)] = off
    ents = {(0, 0): one}                  # row-major index of kron(link3, link2, link1, link0): idx = sum_l s_l 6^l
    stride = 1
    for _ in range(4):
        new: dict = {}
        for (i, j), lp in ents.items():
            for (a, b), f in layer.items():
                new[(i + a * stride, j + b * stride)] = lp * f
        ents, stride = new, stride * 6
    return ents


def _check_cross(kind: str, order: int, ents: dict, base: tuple) -> None:
    """The exact target equals the float `operators.inner_target` at the nominal angles to CROSS_TOL (every entry)."""
    from su2plaq.encodings.rishon import RISHON_NOMINAL, RISHON_NOMINAL_ETA
    from su2plaq.rishon import operators as O

    if kind == "UD":
        eta = RISHON_NOMINAL_ETA
        ref = O.inner_target("UD", None, None, eta=eta)
        th = (eta / base[0], 0.0, 0.0)
    else:
        al, be = RISHON_NOMINAL
        ref = O.inner_target(kind, al, be, order)
        th = (al / base[0], be / base[1], _SQRT2 * be / base[2])
    got = np.zeros((N_INNER, N_INNER), dtype=np.complex128)
    for (i, j), lp in ents.items():
        got[i, j] = lp.evaluate(*th)
    err = float(np.abs(got - ref).max())
    if err > CROSS_TOL:
        raise E.ExactError(f"exact {kind} (order {order}) target deviates from the float target by {err}")


@functools.lru_cache(maxsize=None)
def _exact_target_cached(kind: str, order: int) -> tuple:
    f = _electric_fraction()
    if kind == "UD":
        base, ents = (1, 1, 1), _ud_entries()
    elif kind == "UB":
        base, ents = (1, 1, 1), _ub_entries()
    elif kind == "UE":
        den = f.denominator
        ex = _ue_phase_exps(f.numerator, den)
        base, ents = (den, 1, 1), {(i, i): Laurent3.mono((int(e), 0, 0), E.K_ONE) for i, e in enumerate(ex)}
    elif kind == "step":
        den = f.denominator * (2 if order == 2 else 1)
        ex = _ue_phase_exps(f.numerator, f.denominator)             # units alpha/f.den; order 2 uses alpha/(2 f.den)
        ub = _ub_entries()
        base = (den, 1, 1)
        ents = {}
        for (i, j), lp in ub.items():
            e = int(ex[j]) if order == 1 else int(ex[i] + ex[j])
            ents[(i, j)] = lp.shift((e, 0, 0))
    else:
        raise ValueError(f"unknown kind {kind!r}")
    _check_cross(kind, order, ents, base)
    return base, ents


def exact_target(kind: str, order: int = 1) -> tuple:
    """(base (d_alpha, d_beta, d_gamma), {(i, j): Laurent3}) of the exact inner target (sparse, state indices 0..1295 in sorted code
    order), checked against `operators.inner_target` at the nominal angles to 1e-12.  `kind` in UE, UB, UD (eta in the alpha slot,
    base (1,1,1)), step (order 1: U_B U_E; order 2: U_E(alpha/2) U_B U_E(alpha/2)).  Do not mutate the result (cached)."""
    if kind not in _KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if order not in (1, 2):
        raise ValueError(f"order must be 1 or 2, got {order}")
    return _exact_target_cached(kind, order if kind == "step" else 1)


def _scaled_entries(ents: dict, fa: int, fb: int, fg: int) -> dict:
    return {ij: Laurent3({(a * fa, b * fb, g * fg): v for (a, b, g), v in lp.items()}) for ij, lp in ents.items()}


# --------------------------------------------------------------------------------------------------------------------
# pins
def _q(x) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def _k(k: "E.KNum") -> str:
    return ",".join(_q(c) for c in k.comps())


def target_text(ents: dict) -> str:
    """Canonical text of the target at its own base (= `Cert3.targetText` of the checker): entries by (i, j), terms by exponent."""
    out = []
    for (i, j), lp in sorted(ents.items()):
        terms = ";".join(f"({a},{b},{g})={_k(v)}" for (a, b, g), v in sorted(lp.items()))
        out.append(f"E{i},{j}:{terms}\n")
    return "".join(out)


TARGETS = (("UE", 1), ("UB", 1), ("UD", 1), ("step", 1), ("step", 2))


def compute_pins() -> dict:
    return {f"{kind}:{order}": {"base": list(exact_target(kind, order)[0]),
                                "sha256": hashlib.sha256(target_text(exact_target(kind, order)[1]).encode()).hexdigest()}
            for kind, order in TARGETS}


def render_pins_lean(p: dict) -> str:
    def row(key, kind, order, field):
        arm = f'"{kind}", {order}' if kind == "step" else f'"{kind}", _'
        v = p[key][field]
        return f"  | {arm} => some " + (f'"{v}"' if field == "sha256" else "(" + ", ".join(str(x) for x in v) + ")")

    keys = [(f"{k}:{o}", k, o) for k, o in TARGETS]
    return f'''/-!
# Su2PlaqCert.Rishon.Pins3 — fingerprints of the exporter's exact targets (GENERATED by `python -m su2plaq.rishon.lean_cert pins`; do not edit)

SHA-256 of the canonical text of the exact inner targets of U_E, U_B, the det layer U_D (eta in the first slot) and the first / second
order step (`su2plaq.rishon.lean_cert.target_text`) at their own base `(d_alpha, d_beta, d_gamma)`.  See `Cert3.pinError`.
-/
namespace Su2PlaqCert.Rishon.Pins3

/-- `(d_alpha, d_beta, d_gamma)` of the exact targets. -/
def targetBase (kind : String) (order : Nat) : Option (Nat × Nat × Nat) :=
  match kind, order with
{chr(10).join(row(k, kd, o, "base") for k, kd, o in keys)}
  | _, _ => none

def targetSha256 (kind : String) (order : Nat) : Option String :=
  match kind, order with
{chr(10).join(row(k, kd, o, "sha256") for k, kd, o in keys)}
  | _, _ => none

end Su2PlaqCert.Rishon.Pins3
'''


def write_pins(path=PINS_FILE) -> pathlib.Path:
    path = pathlib.Path(path)
    path.write_text(render_pins_lean(compute_pins()))
    return path


# --------------------------------------------------------------------------------------------------------------------
# checker executable
_BUILT = False


def _checker_exe() -> pathlib.Path:
    """Path of the compiled checker; builds it (`lake build su2plaq_rishon_cert`, a no-op when up to date) once per process."""
    global _BUILT
    exe = P.LEAN_DIR / ".lake" / "build" / "bin" / "su2plaq_rishon_cert"
    if not _BUILT or not exe.exists():
        r = P.build("su2plaq_rishon_cert", timeout=1800)
        if not r["ok"]:
            raise RuntimeError("cannot build the rishon Lean checker:\n" + r["stderr"][-2000:])
        _BUILT = True
    return exe


def checker_sha256() -> str:
    return hashlib.sha256(_checker_exe().read_bytes()).hexdigest()


def _run_checker(args: list, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run([str(_checker_exe()), *args], capture_output=True, text=True, timeout=timeout)


# --------------------------------------------------------------------------------------------------------------------
# gate records
def _exporter_sha() -> str:
    h = hashlib.sha256()
    for f in (pathlib.Path(__file__), pathlib.Path(C.__file__).with_name("exact.py")):
        h.update(f.read_bytes())
    return h.hexdigest()


def _lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def _fractions(theta: float, mode: str, alpha: float, beta: float):
    """(r_alpha, r_beta, r_gamma) Fractions with theta = r_alpha alpha + r_beta beta + r_gamma sqrt2 beta (mode "unit") or
    theta = r_alpha eta, alpha = eta (mode "det"); None if not recognised."""
    if mode == "det":
        f = recognise_angle_single(theta, alpha)
        return None if f is None else (Fraction(f[0], f[1]), Fraction(0), Fraction(0))
    f = recognise_angle(theta, alpha, beta)
    return None if f is None else (Fraction(f[0], f[3]), Fraction(f[1], f[3]), Fraction(f[2], f[3]))


def _gate_records3(ops, perm, mode, alpha, beta, base_min=(1, 1, 1)):
    """(gate records, base (d_alpha, d_beta, d_gamma), per-op exponent fractions) or a reason string (n_a)."""
    fr = []
    d = list(base_min)
    for name, qs, payload in ops:
        if name in ("u", "unitary"):
            return "unitary_gate"
        if name in C._ANGLE_GATES:
            theta = float(payload[0])
            r = _fractions(theta, mode, alpha, beta)
            if r is None:
                return f"non_linear_angle:{name}:{theta!r}"
            fr.append(r)
            h = Fraction(1, 2) if name == "rz" else Fraction(1)
            for s in range(3):
                d[s] = _lcm(d[s], (r[s] * h).denominator)
        elif name in C._PLAIN_GATES:
            fr.append(None)
        else:
            return f"unsupported_gate:{name}"
    recs = []
    for (name, qs, payload), r in zip(ops, fr):
        rec = {"g": name, "q": [perm[q] for q in qs]}
        if r is not None:
            m = [r[s] * d[s] for s in range(3)]
            assert all(x.denominator == 1 for x in m)
            if name == "rz":
                assert all(x.numerator % 2 == 0 for x in m)
            rec["m"] = [int(x) for x in m]
        recs.append(rec)
    return recs, tuple(d), fr


def _plan(qc, mode: str, alpha: float, beta: float, *, with_states: bool, base_min=(1, 1, 1)):
    """Translate `qc` and derive the layout, gate records and base: (ops_canon, recs, base, fr, layout) or an n_a reason string."""
    n = qc.num_qubits
    layout = None
    perm = {q: q for q in range(n)}
    if with_states:
        enc = _encoding()
        try:
            layout = enc.layout_of(qc)
        except ValueError as exc:
            return f"bad_layout:{exc}"
        if len(layout.ancilla) + N_DATA > 62:
            return "too_many_qubits"
        perm = {q: i for i, q in enumerate(layout.data)}
        perm.update({q: N_DATA + k for k, q in enumerate(layout.ancilla)})
    elif n > 62:
        return "too_many_qubits"
    try:
        ops, _gphase = C._translate_export(qc)
    except ValueError as exc:
        return f"disallowed_gate:{exc}"
    if layout is not None and layout.outer:
        outer = set(layout.outer)
        if any(q in outer for _nm, qs, _pl in ops for q in qs):
            return "outer_read"
    res = _gate_records3(ops, perm, mode, alpha, beta, base_min)
    if isinstance(res, str):
        return res
    recs, base, fr = res
    ops_canon = [(nm, tuple(perm[q] for q in qs), pl) for nm, qs, pl in ops]
    return ops_canon, recs, base, fr, layout


_ENC = None


def _encoding():
    global _ENC
    if _ENC is None:
        from su2plaq.compress.spec import get_encoding

        _ENC = get_encoding("rishon")
    return _ENC


def _git_commit() -> str:
    return C._git_commit()


def export_raw_circuit(qc, out_path, *, alpha: float, beta: float):
    """Gates + base only (no states / target), qubits keep the circuit's own indices, for `checker_eval` semantics tests.  Returns the
    path, or an n_a reason string."""
    plan = _plan(qc, "unit", float(alpha), float(beta), with_states=False)
    if isinstance(plan, str):
        return plan
    _ops, recs, base, _fr, _layout = plan
    cert = {"schema": SCHEMA, "circuit_id": "raw-" + hashlib.sha256(json.dumps(recs).encode()).hexdigest()[:12],
            "n_qubits": qc.num_qubits, "n_data": 0, "n_outer": 0,
            "base": {"d_alpha": base[0], "d_beta": base[1], "d_gamma": base[2]}, "gates": recs,
            "provenance": {"git_commit": _git_commit(), "exporter_sha256": _exporter_sha(), "alpha_nominal": alpha,
                           "beta_nominal": beta}}
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert))
    return out_path


# --------------------------------------------------------------------------------------------------------------------
# global phase
def _slots(mode: str, pair) -> tuple:
    return (float(pair[0]), 0.0, 0.0) if mode == "det" else (float(pair[0]), float(pair[1]), _SQRT2 * float(pair[1]))


def _test_states(ents: dict) -> list:
    """Deterministic probe states of the phase fit: spread over the code range plus the state with the widest target column."""
    width: dict = {}
    for (_i, j) in ents:
        width[j] = width.get(j, 0) + 1
    widest = max(sorted(width), key=lambda j: width[j]) if width else 0
    return sorted({0, 1, 324, 648, 972, 1295, widest})


def _float_phase3(ops_canon, fr, mode, slot, base, n_cert, ents_t, base_t, ks, codes):
    """(c, spread): <V col| U |code_k> over the probe states at one angle point; `slot` = (theta_alpha-slot, ..) values of the pair.
    Returns the mean phase estimate c and the largest deviation of any probe state from c (plus the residual norm)."""
    from su2plaq.evaluate import sparse_sim as ss
    from su2plaq.evaluate.evaluator import _ops_to_circuit

    ops_f = []
    for (nm, qs, pl), r in zip(ops_canon, fr):
        if r is None:
            ops_f.append((nm, qs, pl))
        else:
            ops_f.append((nm, qs, (float(r[0]) * slot[0] + float(r[1]) * slot[1] + float(r[2]) * slot[2],)))
    qcf = _ops_to_circuit(ops_f, 0.0, n_cert)
    batch = ss.run_batch(qcf, np.array([codes[k] for k in ks], dtype=np.int64))
    th = (slot[0] / base_t[0], slot[1] / base_t[1], slot[2] / base_t[2])
    cs, resid = [], 0.0
    for col, k in enumerate(ks):
        out: dict = {}
        sel = batch.cols == col
        for key, a in zip(batch.keys[sel].tolist(), batch.amps[sel]):
            out[key] = out.get(key, 0j) + a
        v = {codes[i]: lp.evaluate(*th) for (i, j), lp in ents_t if j == k}
        c = sum(np.conj(val) * out.get(code, 0j) for code, val in v.items())
        resid = max(resid, float(np.sqrt(sum(abs(out.get(code, 0j) - c * val) ** 2 for code, val in v.items())
                                         + sum(abs(a) ** 2 for code, a in out.items() if code not in v))))
        cs.append(c)
    cs = np.array(cs)
    c = complex(np.mean(cs))
    return c, float(max(np.max(np.abs(cs - c)), resid))


def _fit_phase3(cs, slots, base, window=12):
    """(j, a, b, g) with c_i = omega^j z_alpha^a z_beta^b z_gamma^g at every angle point (theta = slot / base), or None; the smallest
    |a| + |b| + |g|, then the smallest j.  Slots that are identically zero at every point (e.g. beta, gamma of the det layer) are not searched."""
    dA, dB, dG = base
    A = np.arange(-window * dA, window * dA + 1, dtype=np.int64)
    B = np.arange(-window * dB, window * dB + 1, dtype=np.int64) if any(s[1] for s in slots) else np.zeros(1, dtype=np.int64)
    G = np.arange(-window * dG, window * dG + 1, dtype=np.int64) if any(s[2] for s in slots) else np.zeros(1, dtype=np.int64)
    ga, gb, gg = (x.ravel() for x in np.meshgrid(A, B, G, indexing="ij"))

    def phase(idx, s):
        return ga[idx] * (s[0] / dA) + gb[idx] * (s[1] / dB) + gg[idx] * (s[2] / dG)

    everything = np.arange(len(ga))
    ph0 = phase(everything, slots[0])
    cand_i, cand_j = [], []
    for j in range(8):
        idx = np.flatnonzero(np.abs(np.exp(1j * (ph0 + j * np.pi / 4)) - cs[0]) < FIT_TOL)
        cand_i.append(idx)
        cand_j.append(np.full(len(idx), j))
    I, J = np.concatenate(cand_i), np.concatenate(cand_j)
    for c, s in zip(cs[1:], slots[1:]):
        ok = np.abs(np.exp(1j * (phase(I, s) + J * (np.pi / 4))) - c) < FIT_TOL
        I, J = I[ok], J[ok]
    if len(I) == 0:
        return None
    i, j = min(zip(I.tolist(), J.tolist()), key=lambda t: (abs(int(ga[t[0]])) + abs(int(gb[t[0]])) + abs(int(gg[t[0]])), t[1]))
    return int(j), int(ga[i]), int(gb[i]), int(gg[i])


# --------------------------------------------------------------------------------------------------------------------
def _export(qc, kind: str, alpha: float, beta: float, order: int, out_path, alt_pairs, mode: str,
            extra_provenance: dict | None = None):
    t0 = time.time()
    if kind not in _KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if (kind == "UD") != (mode == "det"):
        raise ValueError("kind 'UD' is exported with mode 'det' (certify_det_layer) and only that")
    t_base, ents_t = exact_target(kind, order)
    plan = _plan(qc, mode, float(alpha), float(beta), with_states=True, base_min=t_base)
    if isinstance(plan, str):
        return plan
    ops_canon, recs, base, fr, layout = plan
    n_cert = N_DATA + len(layout.ancilla)
    fa, fb, fg = (base[s] // t_base[s] for s in range(3))
    ents = _scaled_entries(ents_t, fa, fb, fg)
    codes = [int(c) for c in _inner_codes()]
    # --- phase c = omega^j z_alpha^a z_beta^b z_gamma^g, fitted from the float simulation at the nominal and alternate points
    pairs = [(alpha, beta)] + [tuple(p) if hasattr(p, "__len__") else (p, 0.0) for p in alt_pairs]
    slots = [_slots(mode, p) for p in pairs]
    ks = _test_states(ents_t)
    items_t = sorted(ents_t.items())
    cs, spread = [], 0.0
    from su2plaq.evaluate import sparse_sim as ss

    try:
        for s in slots:
            c, sp_ = _float_phase3(ops_canon, fr, mode, s, base, n_cert, items_t, t_base, ks, codes)
            cs.append(c)
            spread = max(spread, sp_)
    except ss.SimCapExceeded:
        return "unsimulable"
    unit = all(abs(abs(c) - 1) < 1e-7 for c in cs) and spread < 1e-7
    fit = _fit_phase3([c / abs(c) for c in cs], slots, base) if unit else None
    if fit is None:
        if unit:
            return "phase_not_in_K"
        fit = (0, 0, 0, 0)          # the circuit is not the target up to a phase: let the exact checker reject it
    j_, a_, b_, g_ = fit
    gates_hash = hashlib.sha256(json.dumps(recs).encode()).hexdigest()
    slot_names = ({"alpha": "eta"} if mode == "det"
                  else {"alpha": "alpha", "beta": "beta", "gamma": "sqrt2*beta"})
    cert = {
        "schema": SCHEMA, "circuit_id": f"{kind}-o{order}-{gates_hash[:12]}", "gates_sha256": gates_hash,
        "n_qubits": n_cert, "n_data": N_DATA, "n_outer": 0, "outer_dropped": len(layout.outer),
        "base": {"d_alpha": base[0], "d_beta": base[1], "d_gamma": base[2]},
        "gates": recs, "states": codes,
        "target": {"kind": kind, "order": order,
                   "entries": [[i, j, lp.to_json()] for (i, j), lp in sorted(ents.items())]},
        "phase": {"k": E.omega_power(j_).to_json(), "m": [a_, b_, g_]},
        "provenance": {"kind": kind, "angle_slots": slot_names, "git_commit": _git_commit(), "exporter_sha256": _exporter_sha(),
                       "alpha_nominal": alpha, "beta_nominal": beta, "float_phase_spread": spread,
                       "export_seconds": time.time() - t0, **(extra_provenance or {})},
    }
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert, separators=(",", ":")))
    return out_path


@functools.lru_cache(maxsize=1)
def _inner_codes() -> np.ndarray:
    from su2plaq.rishon import operators as O

    codes = O.inner_codes()
    ref = sorted(sum(int(s) << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(_SECTOR, repeat=4))
    if list(map(int, codes)) != ref:
        raise E.ExactError("inner codes differ from the sector product the checker generates")
    return codes


def export_inner_certificate(qc, kind: str, alpha: float, beta: float, order: int, out_path, *, alt_angles=None,
                             extra_provenance: dict | None = None):
    """Write the certificate JSON of `qc` against the exact (kind in UE, UB, step; order) inner target at the nominal angles
    (`alt_angles` default `ALT_ANGLES`: the phase is fitted at the nominal and alternate pairs, the circuit being re-instantiated at them
    from its recognised angle exponents).  Returns the path or an n_a reason string (`non_linear_angle:<gate>:<theta>`, `unitary_gate`,
    `phase_not_in_K`, `too_many_qubits`, `outer_read`, ...)."""
    from su2plaq.encodings.base import ALT_ANGLES

    if kind == "UD":
        raise ValueError("use certify_det_layer for the det layer")
    return _export(qc, kind, float(alpha), float(beta), int(order), out_path, ALT_ANGLES if alt_angles is None else alt_angles, "unit",
                   extra_provenance)


# --------------------------------------------------------------------------------------------------------------------
# the Python-side pin (refuse a certificate that differs from the exporter's exact data before any Lean run)
def _mismatch(path) -> str | None:
    """Structure and trusted inputs of a circuit certificate against the exporter's exact data; a reason or None.  (The Lean checker
    repeats the structural checks, regenerates the state list and compares the target with its SHA-256 pin.)"""
    try:
        d = json.loads(pathlib.Path(path).read_text())
        if not isinstance(d, dict) or d.get("schema") != SCHEMA:
            return "not a rishon three-angle certificate"
        if d.get("n_data") != N_DATA or d.get("n_outer") != 0 or "states" not in d or "target" not in d:
            return "not a rishon circuit certificate with states and target (n_data 16, n_outer 0)"
        if d["states"] != [int(c) for c in _inner_codes()]:
            return "states differ from the 1296 inner codes"
        tgt = d["target"]
        kind, order = tgt["kind"], int(tgt.get("order", 1))
        t_base, ents_t = exact_target(kind, order)
        b = d["base"]
        got = (b["d_alpha"], b["d_beta"], b["d_gamma"])
        if any((not isinstance(x, int)) or x <= 0 or x % t for x, t in zip(got, t_base)):
            return "base is not a positive multiple of the target's base"
        want = _scaled_entries(ents_t, *(g // t for g, t in zip(got, t_base)))
        have = {(int(e[0]), int(e[1])): Laurent3.from_json(e[2]) for e in tgt["entries"]}
        if want != have or len(have) != len(tgt["entries"]):
            return f"target differs from the exact {kind} target"
        ph = d.get("phase", {})
        if len(ph.get("m", [])) != 3 or not any(E.KNum.from_json(ph["k"]) == E.omega_power(j) for j in range(8)):
            return "bad phase: needs an eighth root of unity k and three integer exponents"
        recorded = d.get("gates_sha256")
        if recorded != hashlib.sha256(json.dumps(d["gates"]).encode()).hexdigest():
            return "gate list does not match its recorded gates_sha256"
    except E.ExactError as exc:
        return f"exporter data unavailable: {exc}"
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, ZeroDivisionError, OverflowError) as exc:
        return f"malformed certificate: {type(exc).__name__}: {exc}"
    return None


def check_inner_certificate(path, timeout: float = 900.0) -> LeanCert:
    """Compare the trusted inputs with the exporter's exact data, then `su2plaq_rishon_cert check <path>`: ACCEPT -> certified,
    REJECT <reason> -> rejected, anything else -> failed."""
    t0 = time.time()
    why = _mismatch(path)
    if why is not None:
        return LeanCert("rejected", why, str(path), time.time() - t0, "")
    try:
        sha = checker_sha256()
        r = _run_checker(["check", str(path)], timeout)
    except subprocess.TimeoutExpired:
        return LeanCert("failed", f"timeout after {timeout}s", str(path), time.time() - t0, "")
    except (RuntimeError, OSError) as exc:
        return LeanCert("failed", str(exc), str(path), time.time() - t0, "")
    line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    dt = time.time() - t0
    if line == "ACCEPT":
        return LeanCert("certified", "", str(path), dt, sha)
    if line.startswith("REJECT"):
        return LeanCert("rejected", line[len("REJECT"):].strip(), str(path), dt, sha)
    return LeanCert("failed", f"checker output {line!r} stderr {r.stderr.strip()[-300:]!r}", str(path), dt, sha)


def _certify(qc, kind, alpha, beta, order, out_dir, timeout, alt, mode, extra_provenance=None) -> LeanCert:
    t0 = time.time()
    out_dir = pathlib.Path(out_dir) if out_dir is not None else C.CERT_DIR
    tmp = out_dir / f"{kind}-o{order}-pending-{abs(hash(id(qc))) % 10**8}.json"
    try:
        res = _export(qc, kind, alpha, beta, order, tmp, alt, mode, extra_provenance)
    except E.ExactError as exc:
        return LeanCert("failed", f"exact export failed: {exc}", None, time.time() - t0, "")
    if isinstance(res, str):
        return LeanCert("n_a", res, None, time.time() - t0, "")
    final = out_dir / (json.loads(res.read_text())["circuit_id"] + ".json")
    res.replace(final)
    cert = check_inner_certificate(final, timeout=timeout)
    cert.seconds = time.time() - t0
    return cert


def certify_circuit_kind(qc, kind: str, alpha: float, beta: float, order: int, out_dir=None, timeout: float = 900.0,
                         extra_provenance: dict | None = None) -> LeanCert:
    """export_inner_certificate + check_inner_certificate without a TaskSpec (alternate pairs = `ALT_ANGLES`)."""
    from su2plaq.encodings.base import ALT_ANGLES

    return _certify(qc, kind, float(alpha), float(beta), int(order), out_dir, timeout, ALT_ANGLES, "unit", extra_provenance)


def certify_det_layer(qc, eta: float, out_dir=None, timeout: float = 900.0) -> LeanCert:
    """The det layer U_D(eta) (16 data qubits) against the exact closed form of `operators.inner_target("UD", eta=eta)` for ALL eta:
    the same checker and schema with eta in the first formal slot (gate exponents (m, 0, 0), `provenance.angle_slots = {"alpha": "eta"}`).
    Alternate points for the phase fit: `RISHON_ALT_ETA`."""
    from su2plaq.encodings.rishon import RISHON_ALT_ETA

    return _certify(qc, "UD", float(eta), 0.0, 1, out_dir, timeout, tuple((e,) for e in RISHON_ALT_ETA), "det")


# --------------------------------------------------------------------------------------------------------------------
# the exporter rule of prompts/204 section 6.4
ROTATION_GATES = ("rz", "p", "crz", "crx", "cp")


def rotation_fits(qc, alpha: float, beta: float) -> list:
    """The angle fit (m_alpha, m_beta, m_gamma, d) | None of every rotation gate of `qc` (circuit order) at (alpha, beta): the quantity
    `robust.robust_metrics` records as `angle_fit`."""
    return [recognise_angle(float(i.operation.params[0]), alpha, beta) for i in qc.data if i.operation.name in ROTATION_GATES]


def confirm_angle_fit(program_path, spec, root=None) -> dict:
    """prompts/204 section 6.4: rebuild the program at the nominal pair and at the 20 pairs of `ANGLE_SET` (build only, no T counts) and
    check that the gate skeleton is the same and that the angle fit of every rotation (`recognise_angle` at the nominal pair) reproduces
    the angle at every pair to 1e-9 (the `rho = 0` test of `robust.robust_metrics`).  -> {"confirmed", "angle_fit", "reason"}."""
    from su2plaq.compress.robust import ANGLE_SET
    from su2plaq.rishon.compress import evaluate as EV

    f = pathlib.Path(program_path)
    if not f.is_absolute():
        base = pathlib.Path(root) if root is not None else C.ROOT
        f = base / f if (base / f).exists() else C.ROOT / f
    specs = [spec.with_angles(a, b) for a, b in ANGLE_SET]
    circuits, _ = EV._build_in_subprocess(f.read_bytes(), [spec, *specs], EV.BUILD_TIMEOUT_S)
    nominal, circuits = circuits[0], circuits[1:]
    if len({tuple(map(tuple, EV.skeleton(c))) for c in [nominal, *circuits]}) != 1:
        return {"confirmed": False, "angle_fit": None, "reason": "the gate skeleton changes over the angle set"}
    fits = rotation_fits(nominal, spec.alpha, spec.beta)
    if any(x is None for x in fits):
        return {"confirmed": False, "angle_fit": fits, "reason": "a rotation angle is not linear in (alpha, beta, sqrt2 beta)"}
    for (a, b), c in zip(ANGLE_SET, circuits):
        for fit, inst in zip(fits, (i for i in c.data if i.operation.name in ROTATION_GATES)):
            ma, mb, mg, d = fit
            if abs((ma * a + mb * b + mg * _SQRT2 * b) / d - float(inst.operation.params[0])) > LINEAR_TOL:
                return {"confirmed": False, "angle_fit": fits, "reason": f"the fit does not reproduce the angle at the pair ({a}, {b})"}
    return {"confirmed": True, "angle_fit": fits, "reason": ""}


def certify_circuit(qc, spec, out_dir=None, timeout: float = 900.0, *, angle_fit: dict | None = None) -> LeanCert:
    """Export + check with kind / angles / order from the TaskSpec; status certified | rejected | n_a | failed.  `out_dir` default
    compress/lean/certs/ (gitignored *.json).  `angle_fit` (the result of `confirm_angle_fit`, for archive entries; prompts/204 section 6.4):
    when given, the entry is certified only if it is confirmed and the exponents the exporter emits (the nominal `rotation_fits`) equal the
    confirmed fit; otherwise status `n_a`, reason `angle_fit_not_confirmed: <why>`."""
    if getattr(spec, "encoding", "rishon") != "rishon":
        return LeanCert("n_a", f"unsupported_encoding:{spec.encoding}", None, 0.0, "")
    if angle_fit is not None:
        mine = rotation_fits(qc, float(spec.alpha), float(spec.beta))
        theirs = angle_fit.get("angle_fit")
        same = theirs is not None and [None if x is None else tuple(x) for x in mine] == [None if x is None else tuple(x) for x in theirs]
        if not angle_fit.get("confirmed") or not same:
            why = angle_fit.get("reason") or "the exporter's exponents differ from the angle fit of the entry"
            return LeanCert("n_a", f"angle_fit_not_confirmed: {why}", None, 0.0, "")
    return certify_circuit_kind(qc, spec.kind, float(spec.alpha), float(spec.beta), int(spec.order), out_dir, timeout)


# --------------------------------------------------------------------------------------------------------------------
_DEPENDS_RE = re.compile(r"'([^']+)' depends on axioms:\s*\[(.*?)\]", re.S)
_NONE_RE = re.compile(r"'([^']+)' does not depend on any axioms")


def check_theorem_file(path, timeout: float = 1800.0) -> dict:
    """`lake env lean <file>` after building the project modules the file imports; the printed axioms.
    -> {"status": "certified" | "rejected" | "error", "axioms": list[str], "seconds", "detail"}: certified = exit 0, no error and a
    `#print axioms` line; rejected = `native_decide` evaluated the statement to false; error = anything else."""
    t0 = time.time()
    path = pathlib.Path(path).resolve()
    mods = [m for m in re.findall(r"^import\s+(Su2PlaqCert\.[\w.]+)", path.read_text(), re.M)]
    for mod in dict.fromkeys(["Su2PlaqCert.Rishon.Check3", *mods]):
        b = P.build("+" + mod, timeout=max(1.0, timeout - (time.time() - t0)))
        if not b["ok"]:
            return {"status": "error", "axioms": [], "seconds": time.time() - t0,
                    "detail": f"build of {mod} failed: " + (b["stdout"] + b["stderr"])[-1500:]}
    try:
        r = P.lake(["env", "lean", str(path)], timeout=max(1.0, timeout - (time.time() - t0)))
    except subprocess.TimeoutExpired:
        return {"status": "error", "axioms": [], "seconds": time.time() - t0, "detail": f"TIMEOUT after {timeout}s"}
    text = r.stdout + "\n" + r.stderr
    axioms: list = []
    found = False
    for m in _DEPENDS_RE.finditer(text):
        found = True
        axioms += [a.strip() for a in m.group(2).replace("\n", " ").split(",") if a.strip()]
    if _NONE_RE.search(text):
        found = True
    if r.returncode != 0 or ": error" in text:
        rejected = "evaluated that the proposition" in text and "is false" in text
        return {"status": "rejected" if rejected else "error", "axioms": axioms, "seconds": time.time() - t0, "detail": text[-1500:]}
    if not found:
        return {"status": "error", "axioms": axioms, "seconds": time.time() - t0, "detail": "no #print axioms output\n" + text[-1500:]}
    return {"status": "certified", "axioms": sorted(set(axioms)), "seconds": time.time() - t0, "detail": text[-500:]}


def checker_eval(cert_path, input_index: int, timeout: float = 900.0) -> list:
    """`su2plaq_rishon_cert eval <cert> <k>`: exact output of the gate list on the basis state with integer `k` as
    [(basis integer, Laurent3)]."""
    r = _run_checker(["eval", str(cert_path), str(int(input_index))], timeout)
    if r.returncode != 0:
        raise RuntimeError(f"checker eval failed: {r.stdout.strip()} {r.stderr.strip()}")
    data = json.loads(r.stdout)
    out = []
    for t in data["out"]:
        lp = Laurent3()
        for ma, mb, mg, k in t["terms"]:
            lp = lp + Laurent3.mono((int(ma), int(mb), int(mg)), E.KNum.from_json(k))
        out.append((int(t["key"]), lp))
    return out


def write_theorem_file(cert_path, theorem_name: str, out_path) -> pathlib.Path:
    """Write `import Su2PlaqCert.Rishon.Check3` + the certificate JSON as a Lean string literal + `theorem <name> :
    Su2PlaqCert.Rishon.checkJsonString certJson = true := by native_decide` + `#print axioms <name>` (standard axioms plus one
    per-theorem `native_decide` axiom: compiler trust; `checkJsonString` parses the literal and runs `Su2PlaqCert.Rishon.check`).
    Refuses a certificate that differs from the exporter's exact data.  Elaborate with `cd lean && lake env lean <out_path>`."""
    cert_path, out_path = pathlib.Path(cert_path), pathlib.Path(out_path)
    why = _mismatch(cert_path)
    if why is not None:
        raise ValueError(f"refusing to write a theorem file for a certificate that differs from the exporter's exact data: {why}")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", theorem_name):
        raise ValueError(f"bad theorem name {theorem_name!r} (alphanumeric/underscore)")
    text = cert_path.read_text()
    d = json.loads(text)
    lit = text.replace("\\", "\\\\").replace('"', '\\"')
    if "\n" in lit or "\r" in lit:
        raise ValueError("certificate JSON must be a single line")
    prov = d.get("provenance", {})
    head = (
        "import Su2PlaqCert.Rishon.Check3\n\n"
        "/-! Generated by `su2plaq.rishon.lean_cert.write_theorem_file` -- do not edit.\n"
        f"circuit_id {d.get('circuit_id')}; git {prov.get('git_commit')}; exporter {prov.get('exporter_sha256')};\n"
        f"certificate sha256 {hashlib.sha256(text.encode()).hexdigest()}; {len(d['gates'])} gates, {d['n_qubits']} qubits "
        f"({d.get('outer_dropped', 0)} untouched outer qubits dropped).\n"
        "`native_decide` runs the compiled checker `Su2PlaqCert.Rishon.checkJsonString` (trust: Lean compiler + checker source). -/\n\n")
    body = (f'def certJson : String := "{lit}"\n\n'
            f"theorem {theorem_name} : Su2PlaqCert.Rishon.checkJsonString certJson = true := by native_decide\n\n"
            f"#print axioms {theorem_name}\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(head + body)
    return out_path


def write_general_step_theorem(out_path=None, theorem_name: str = "rishon_cert_general_step", cert_dir=None) -> pathlib.Path:
    """Certify the general step circuit (`baselines.general_circuit`, ladder "ccx") and write its theorem file
    (default `lean/certs/rishon-general-step.lean`); ValueError if the circuit is not certified."""
    from su2plaq.rishon.compress import baselines as BL
    from su2plaq.rishon.compress.spec import rishon_spec

    spec = rishon_spec("step")
    cert = certify_circuit(BL.general_circuit(spec), spec, out_dir=cert_dir)
    if cert.status != "certified":
        raise ValueError(f"the general step circuit is {cert.status}: {cert.reason}")
    out = pathlib.Path(out_path) if out_path is not None else P.LEAN_DIR / "certs" / "rishon-general-step.lean"
    return write_theorem_file(cert.cert_path, theorem_name, out)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["pins"]:
        print(write_pins())
        return 0
    if argv[:1] == ["general-step-theorem"]:
        print(write_general_step_theorem(argv[1] if len(argv) > 1 else None))
        return 0
    print("usage: python -m su2plaq.rishon.lean_cert (pins | general-step-theorem [out.lean])", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
