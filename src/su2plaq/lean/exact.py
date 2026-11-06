"""Exact arithmetic for the Lean certificates (prompts/006 §5, docs/METHODS.md §11.2).

Field K = Q(i, sqrt2, sqrt3), stored as eight rationals (a, b, c, d, e, f, g, h) for
a + b i + c sqrt2 + d i sqrt2 + e sqrt3 + f i sqrt3 + g sqrt6 + h i sqrt6 (the same layout as `Su2PlaqCert.K`).
Everything the certificates need is computed in exact rational arithmetic (sympy nullspaces, Racah's closed formula for
Clebsch-Gordan coefficients); floats are used only to cross-check against the validated float code (<= 1e-12 per entry)
and, in `KNum.recognise`, to recognise phases.
"""
from __future__ import annotations

import functools
import hashlib
import itertools
import math
import pathlib
import pickle
from fractions import Fraction
from typing import Iterable

import numpy as np

_SQ = (1.0, math.sqrt(2.0), math.sqrt(3.0), math.sqrt(6.0))
CROSS_TOL = 1e-12


class ExactError(RuntimeError):
    """An exact computation did not produce an element of K (or an expected identity failed)."""


def _fr(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(x)


def _fmt(q: Fraction) -> str:
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


# --------------------------------------------------------------------------------------------------------------------
class KNum:
    """Element of K = Q(i, sqrt2, sqrt3); eight Fraction components a..h."""

    __slots__ = ("a", "b", "c", "d", "e", "f", "g", "h")

    def __init__(self, a=0, b=0, c=0, d=0, e=0, f=0, g=0, h=0):
        self.a, self.b, self.c, self.d = _fr(a), _fr(b), _fr(c), _fr(d)
        self.e, self.f, self.g, self.h = _fr(e), _fr(f), _fr(g), _fr(h)

    # pickling with __slots__
    def __getstate__(self):
        return self.comps()

    def __setstate__(self, st):
        self.a, self.b, self.c, self.d, self.e, self.f, self.g, self.h = st

    def comps(self) -> tuple:
        return (self.a, self.b, self.c, self.d, self.e, self.f, self.g, self.h)

    @staticmethod
    def of(x) -> "KNum":
        return x if isinstance(x, KNum) else KNum(x)

    def is_zero(self) -> bool:
        return not any(self.comps())

    def is_real(self) -> bool:
        return not (self.b or self.d or self.f or self.h)

    def __bool__(self) -> bool:
        return not self.is_zero()

    def __eq__(self, other) -> bool:
        if not isinstance(other, KNum):
            try:
                other = KNum.of(other)
            except (TypeError, ValueError):
                return NotImplemented
        return self.comps() == other.comps()

    def __hash__(self) -> int:
        return hash(self.comps())

    def __neg__(self) -> "KNum":
        return KNum(*[-x for x in self.comps()])

    def __add__(self, other) -> "KNum":
        o = KNum.of(other)
        return KNum(*[x + y for x, y in zip(self.comps(), o.comps())])

    __radd__ = __add__

    def __sub__(self, other) -> "KNum":
        o = KNum.of(other)
        return KNum(*[x - y for x, y in zip(self.comps(), o.comps())])

    def __rsub__(self, other) -> "KNum":
        return KNum.of(other) - self

    @staticmethod
    def _mulg(a, b, c, d, a2, b2, c2, d2):
        # product in Q(i, sqrt2), basis (1, i, sqrt2, i sqrt2)
        return (a * a2 - b * b2 + 2 * (c * c2 - d * d2),
                a * b2 + b * a2 + 2 * (c * d2 + d * c2),
                a * c2 + c * a2 - b * d2 - d * b2,
                a * d2 + d * a2 + b * c2 + c * b2)

    def __mul__(self, other) -> "KNum":
        if not isinstance(other, KNum):
            q = _fr(other)
            return KNum(*[q * x for x in self.comps()])
        x, y = self, other
        mg = KNum._mulg
        p = mg(x.a, x.b, x.c, x.d, y.a, y.b, y.c, y.d)
        if not (x.e or x.f or x.g or x.h or y.e or y.f or y.g or y.h):
            return KNum(*p)
        q = mg(x.e, x.f, x.g, x.h, y.e, y.f, y.g, y.h)
        r = mg(x.a, x.b, x.c, x.d, y.e, y.f, y.g, y.h)
        s = mg(x.e, x.f, x.g, x.h, y.a, y.b, y.c, y.d)
        return KNum(p[0] + 3 * q[0], p[1] + 3 * q[1], p[2] + 3 * q[2], p[3] + 3 * q[3],
                    r[0] + s[0], r[1] + s[1], r[2] + s[2], r[3] + s[3])

    __rmul__ = __mul__

    def conj(self) -> "KNum":
        return KNum(self.a, -self.b, self.c, -self.d, self.e, -self.f, self.g, -self.h)

    def inv(self) -> "KNum":
        """Multiplicative inverse (x * conj-type products down to Q); raises on zero."""
        if self.is_zero():
            raise ZeroDivisionError("inverse of 0 in K")
        # Galois conjugates over Q: sign flips of (i, sqrt2, sqrt3); the norm is the product of the other seven.
        def gal(x, si, s2, s3):
            a, b, c, d, e, f, g, h = x.comps()
            # i -> si*i ; sqrt2 -> s2*sqrt2 ; sqrt3 -> s3*sqrt3 ; sqrt6 -> s2*s3*sqrt6
            return KNum(a, si * b, s2 * c, si * s2 * d, s3 * e, si * s3 * f, s2 * s3 * g, si * s2 * s3 * h)
        prod = KNum(1)
        for si, s2, s3 in itertools.product((1, -1), repeat=3):
            if (si, s2, s3) != (1, 1, 1):
                prod = prod * gal(self, si, s2, s3)
        n = self * prod
        if not (n.is_real() and not (n.c or n.e or n.g)):
            raise ExactError("norm of a K element is not rational")
        return prod * (1 / n.a)

    def __truediv__(self, other) -> "KNum":
        if isinstance(other, KNum):
            return self * other.inv()
        return self * (1 / _fr(other))

    def to_complex(self) -> complex:
        a, b, c, d, e, f, g, h = (float(x) for x in self.comps())
        re = a + c * _SQ[1] + e * _SQ[2] + g * _SQ[3]
        im = b + d * _SQ[1] + f * _SQ[2] + h * _SQ[3]
        return complex(re, im)

    def to_json(self) -> list[str]:
        return [_fmt(x) for x in self.comps()]

    @staticmethod
    def from_json(lst: Iterable) -> "KNum":
        return KNum(*[Fraction(s) for s in lst])

    def __repr__(self) -> str:
        names = ("", "i", "r2", "i*r2", "r3", "i*r3", "r6", "i*r6")
        terms = [f"{x}{('*' + n) if n else ''}" for x, n in zip(self.comps(), names) if x]
        return "KNum(" + (" + ".join(terms) if terms else "0") + ")"

    @staticmethod
    def recognise(z: complex, tol: float = 1e-12) -> "KNum | None":
        """Lattice search for z = (A + B sqrt2 + C sqrt3 + D sqrt6) / den (+ i * the same) over denominators 2^a 3^b <= 48,
        |numerators| <= 16.  Returns the first (smallest-denominator) match within `tol`, or None."""
        re = _recognise_real(z.real, tol)
        im = _recognise_real(z.imag, tol)
        if re is None or im is None:
            return None
        return KNum(re[0], im[0], re[1], im[1], re[2], im[2], re[3], im[3])


_DENS = sorted({2 ** i * 3 ** j for i in range(0, 6) for j in range(0, 4) if 2 ** i * 3 ** j <= 48})
_BND = 16


@functools.lru_cache(maxsize=1)
def _grid():
    r = np.arange(-_BND, _BND + 1)
    A, B, C, D = np.meshgrid(r, r, r, r, indexing="ij")
    val = A + B * _SQ[1] + C * _SQ[2] + D * _SQ[3]
    return val.ravel(), np.stack([A.ravel(), B.ravel(), C.ravel(), D.ravel()], axis=1)


def _recognise_real(x: float, tol: float):
    if abs(x) < tol:
        return (Fraction(0),) * 4
    val, coef = _grid()
    for den in _DENS:
        err = np.abs(val - x * den)
        i = int(np.argmin(err))
        if err[i] <= tol * den:
            return tuple(Fraction(int(c), den) for c in coef[i])
    return None


# Constants of K
K_ONE = KNum(1)
K_I = KNum(0, 1)
K_OMEGA = KNum(0, 0, Fraction(1, 2), Fraction(1, 2))     # e^{i pi/4} = (sqrt2 + i sqrt2)/2


def omega_power(j: int) -> KNum:
    out = K_ONE
    for _ in range(j % 8):
        out = out * K_OMEGA
    return out


@functools.lru_cache(maxsize=None)
def sqrt_rational(q: Fraction) -> KNum:
    """sqrt(q) for q >= 0 rational, as an element of K; raises ExactError unless the squarefree part of numerator*denominator
    is 1, 2, 3 or 6."""
    q = _fr(q)
    if q < 0:
        raise ExactError("sqrt of a negative rational")
    if q == 0:
        return KNum(0)
    # sqrt(p/r) = sqrt(p*r)/r ; p*r = f^2 * s with s squarefree
    n = q.numerator * q.denominator
    f, s, m = 1, 1, n
    d = 2
    while d * d <= m:
        while m % (d * d) == 0:
            m //= d * d
            f *= d
        d += 1
    s = m                                    # remaining part is squarefree
    base = Fraction(f, q.denominator)
    if s == 1:
        return KNum(base)
    if s == 2:
        return KNum(0, 0, base)
    if s == 3:
        return KNum(0, 0, 0, 0, base)
    if s == 6:
        return KNum(0, 0, 0, 0, 0, 0, base)
    raise ExactError(f"sqrt({q}) is not in Q(sqrt2, sqrt3) (squarefree part {s})")


# --------------------------------------------------------------------------------------------------------------------
class Laurent(dict):
    """Laurent polynomial in (z_alpha, z_beta) over K: dict[(m_alpha, m_beta)] -> KNum (no zero coefficients)."""

    @staticmethod
    def mono(exp: tuple[int, int], k: KNum) -> "Laurent":
        out = Laurent()
        if not KNum.of(k).is_zero():
            out[(int(exp[0]), int(exp[1]))] = KNum.of(k)
        return out

    def __add__(self, other: "Laurent") -> "Laurent":
        out = Laurent(self)
        for e, k in other.items():
            s = out[e] + k if e in out else k
            if s.is_zero():
                out.pop(e, None)
            else:
                out[e] = s
        return out

    def scale(self, k: KNum) -> "Laurent":
        k = KNum.of(k)
        if k.is_zero():
            return Laurent()
        return Laurent({e: v * k for e, v in self.items()})

    def shift(self, exp: tuple[int, int]) -> "Laurent":
        return Laurent({(e[0] + exp[0], e[1] + exp[1]): v for e, v in self.items()})

    def __mul__(self, other) -> "Laurent":
        if not isinstance(other, Laurent):
            return self.scale(KNum.of(other))
        out = Laurent()
        for e2, k2 in other.items():
            out = out + self.shift(e2).scale(k2)
        return out

    def evaluate(self, theta_alpha: float, theta_beta: float) -> complex:
        tot = 0j
        for (ma, mb), k in self.items():
            tot += k.to_complex() * np.exp(1j * (ma * theta_alpha + mb * theta_beta))
        return complex(tot)

    def to_json(self) -> list:
        return [[[ma, mb], k.to_json()] for (ma, mb), k in sorted(self.items())]

    @staticmethod
    def from_json(lst) -> "Laurent":
        out = Laurent()
        for (e, k) in lst:
            out = out + Laurent.mono((int(e[0]), int(e[1])), KNum.from_json(k))
        return out


def rational_multiple(theta: float, base: float, max_den: int = 64, tol: float = 1e-12) -> Fraction | None:
    """r in Q with denominator <= max_den and |theta - r * base| <= tol, or None.  (theta = 0 gives 0.)"""
    if abs(theta) <= tol:
        return Fraction(0)
    if base == 0:
        return None
    r = Fraction(theta / base).limit_denominator(max_den)
    return r if abs(theta - float(r) * base) <= tol else None


# --------------------------------------------------------------------------------------------------------------------
# Exact corner singlets
def _exact_spin_gens(j: float):
    import sympy as sp

    if abs(j) < 1e-12:
        z = sp.zeros(1, 1)
        return [z, z, z]
    if abs(j - 0.5) < 1e-12:
        half = sp.Rational(1, 2)
        return [sp.Matrix([[0, half], [half, 0]]), sp.Matrix([[0, -sp.I * half], [sp.I * half, 0]]),
                sp.Matrix([[half, 0], [0, -half]])]
    raise NotImplementedError("exact corner singlets are implemented for spins 0 and 1/2 only")


def _sp_to_fraction(x) -> Fraction:
    import sympy as sp

    x = sp.nsimplify(sp.expand(x))
    if x.is_Rational:
        return Fraction(int(x.p), int(x.q))
    raise ExactError(f"not a rational: {x}")


@functools.lru_cache(maxsize=None)
def _exact_corner_singlets_cached(js: tuple, roles: tuple) -> tuple:
    import sympy as sp

    from su2plaq.exact.physical import corner_singlets

    dims = [int(round(2 * j + 1)) for j in js]

    def embed(op, pos):
        out = sp.Matrix([[1]])
        for q, d in enumerate(dims):
            out = sp.kronecker_product(out, op if q == pos else sp.eye(d))
        return out

    gens = []
    for e, (j, role) in enumerate(zip(js, roles)):
        Jm = _exact_spin_gens(j)
        gens.append([embed(-Jm[a].T if role == "out" else Jm[a], e) for a in range(3)])
    G = [sum((g[a] for g in gens), sp.zeros(*gens[0][0].shape)) for a in range(3)]
    C = sum((g * g for g in G), sp.zeros(*G[0].shape)).applyfunc(sp.expand)
    Gin = [gens[0][a] + gens[1][a] for a in range(3)]
    Cin = sum((g * g for g in Gin), sp.zeros(*G[0].shape)).applyfunc(sp.expand)
    fvecs, fJs = corner_singlets(js, roles)             # float columns (J ascending) for the sign cross-check
    n_kernel = len(C.nullspace())
    if n_kernel != fvecs.shape[1]:
        raise ExactError("exact corner kernel dimension differs from the float one")
    cols = []
    D = C.shape[0]
    for J in fJs:
        tj = int(round(2 * J))
        lam = sp.Rational(tj * (tj + 2), 4)               # J (J + 1)
        ns = sp.Matrix.vstack(C, Cin - lam * sp.eye(D)).nullspace()
        if len(ns) != 1:
            raise ExactError(f"corner eigenspace for J={J} has dimension {len(ns)}")
        v = ns[0].applyfunc(sp.expand)
        if any(sp.im(x) != 0 for x in v):
            raise ExactError("corner singlet is not real")
        r = [_sp_to_fraction(sp.re(x)) for x in v]
        norm2 = sum(x * x for x in r)
        mx = max(abs(x) for x in r)
        first = next(i for i, x in enumerate(r) if abs(x) == mx)
        sgn = 1 if r[first] > 0 else -1               # METHODS rule: first maximal-modulus component positive
        scale = sqrt_rational(1 / norm2)
        col = [scale * (sgn * x) for x in r]
        cols.append(col)
    for c, col in enumerate(cols):                    # cross-check against the float vectors
        err = max(abs(k.to_complex() - fvecs[i, c]) for i, k in enumerate(col))
        if err > CROSS_TOL:
            raise ExactError(f"exact corner singlet deviates from float by {err}")
    return tuple(tuple(c) for c in cols), tuple(float(J) for J in fJs)


def exact_corner_singlets(js, roles) -> list[list[KNum]]:
    """Exact columns of `physical.corner_singlets(js, roles)` (same J ordering and phase rule), as lists of KNum over the
    product index of the ends (end 0 most significant)."""
    cols, _ = _exact_corner_singlets_cached(tuple(float(j) for j in js), tuple(roles))
    return [list(c) for c in cols]


# --------------------------------------------------------------------------------------------------------------------
# Exact physical basis (CG convention) and the Paulo-encoded codes
def exact_physical_basis(convention: str = "cg") -> list[dict]:
    """The 433 physical states: [{"label", "keys": int64[], "amps": KNum[]}] in basis order; keys are the electric
    multi-indices of `physical.physical_basis(convention)`.  Cross-checked against the float basis (<= 1e-12 per entry)."""
    return list(_exact_basis_cached(convention))


@functools.lru_cache(maxsize=None)
def _exact_basis_cached(convention: str) -> tuple:
    from su2plaq.exact.physical import _BASE, _NL, physical_basis, to_convention  # noqa: PLC0415
    from su2plaq.geometry import plaquette_diagram
    from su2plaq.su2.algebra import LinkSpace, m_values

    cg = physical_basis(convention="cg")
    d = plaquette_diagram()
    ls = LinkSpace(0.5)
    spins = ls.spins
    local = {j: np.array([[ls.index[(j, ma, mb)] for mb in m_values(j)] for ma in m_values(j)]) for j in spins}
    corner_ends = [c.ends for c in d.corners]
    out = []
    for jconf in itertools.product(spins, repeat=_NL):
        per_corner = []
        for ends in corner_ends:
            js = tuple(jconf[i] for i, _ in ends)
            roles = tuple(r for _, r in ends)
            cols, Js = _exact_corner_singlets_cached(tuple(float(j) for j in js), tuple(roles))
            if not cols:
                per_corner = None
                break
            per_corner.append((ends, js, cols, Js))
        if per_corner is None:
            continue
        for combo in itertools.product(*[range(len(pc[2])) for pc in per_corner]):
            # terms: list of (tuple of leg indices, amplitude) over all legs in corner order
            terms = [((), K_ONE)]
            legs = []
            for (ends, js, cols, _Js), c in zip(per_corner, combo):
                dims = [int(round(2 * j + 1)) for j in js]
                vec = cols[c]
                new_terms = []
                nz = [(flat, v) for flat, v in enumerate(vec) if not v.is_zero()]
                for flat, v in nz:
                    idx, rem = [], flat
                    for dd in reversed(dims):
                        idx.append(rem % dd)
                        rem //= dd
                    idx = tuple(reversed(idx))
                    for tup, a in terms:
                        new_terms.append((tup + idx, a * v))
                terms = new_terms
                legs += list(ends)
            keys, amps = [], []
            for tup, a in terms:
                key = 0
                for i in range(_NL):
                    mL = mR = 0
                    for k, (link, role) in enumerate(legs):
                        if link == i:
                            if role == "out":
                                mL = tup[k]
                            else:
                                mR = tup[k]
                    key += int(local[jconf[i]][mL, mR]) * _BASE ** i
                keys.append(key)
                amps.append(a)
            order = np.argsort(keys)
            label = (tuple(float(x) for x in jconf), tuple(float(per_corner[q][3][combo[q]]) for q in range(4)))
            out.append({"label": label, "keys": np.array(keys, dtype=np.int64)[order], "amps": [amps[i] for i in order]})
    if len(out) != cg.dim:
        raise ExactError(f"exact basis has {len(out)} states, float basis {cg.dim}")
    for st, lab, fk, fa in zip(out, cg.labels, cg.keys, cg.amps):
        if st["label"] != lab:
            raise ExactError("exact/float basis label mismatch")
        o = np.argsort(fk)
        if not np.array_equal(st["keys"], fk[o]):
            raise ExactError("exact/float basis key mismatch")
        err = max((abs(k.to_complex() - a) for k, a in zip(st["amps"], fa[o])), default=0.0)
        if err > CROSS_TOL:
            raise ExactError(f"exact basis deviates from float by {err}")
    if convention == "cg":
        return tuple(out)
    if convention == "paulo":
        return tuple(_to_paulo(out))
    raise ValueError(f"unknown convention {convention!r}")


def _paulo_perm_sign():
    from su2plaq.su2.algebra import paulo_adapter

    V = paulo_adapter()
    perm = np.array([int(np.nonzero(V[:, c])[0][0]) for c in range(5)], dtype=np.int64)
    sign = [int(V[perm[c], c]) for c in range(5)]
    return perm, sign


def _to_paulo(states):
    perm, sign = _paulo_perm_sign()
    res = []
    for st in states:
        nk = np.zeros_like(st["keys"])
        amps = []
        for key, a in zip(st["keys"], st["amps"]):
            nkey, s = 0, 1
            for i in range(12):
                c = (int(key) // 5 ** i) % 5
                nkey += int(perm[c]) * 5 ** i
                s *= sign[c]
            amps.append(a * s)
            nk[len(amps) - 1] = nkey
        o = np.argsort(nk)
        res.append({"label": st["label"], "keys": nk[o], "amps": [amps[i] for i in o]})
    return res


_ENC_CACHE: dict = {}


def exact_encoded_states(enc) -> list[dict]:
    """Exact version of `enc.physical_vectors()` for the twelve-qubit encoding: [{"codes": int[], "amps": KNum[]}] with the
    codes in the canonical (data|outer) frame (bit i < 12: data qubit i; bit 12+j: outer qubit j).  Cross-checked against
    `physical_vectors()` (<= 1e-12 per entry)."""
    if enc.name in _ENC_CACHE:
        return _ENC_CACHE[enc.name]
    st_paulo = _exact_basis_cached("paulo")
    ev = enc.physical_vectors()
    out = []
    for st, codes_f, amps_f in zip(st_paulo, ev.codes, ev.amps):
        codes = np.zeros(len(st["keys"]), dtype=np.int64)
        for l in range(4):
            codes |= enc._code3[(st["keys"] // 5 ** l) % 5] << (3 * l)
        for k in range(8):
            p = (st["keys"] // 5 ** (4 + k)) % 5
            b = enc._b_of_p[k][p]
            if np.any(b < 0):
                raise ExactError("outer far end is not '-' in Paulo labels")
            codes |= b << (12 + 2 * k)
        o = np.argsort(codes)
        codes, amps = codes[o], [st["amps"][i] for i in o]
        of = np.argsort(codes_f)
        if not np.array_equal(codes, np.asarray(codes_f)[of]):
            raise ExactError("exact/float encoded codes differ")
        err = max((abs(k.to_complex() - a) for k, a in zip(amps, np.asarray(amps_f)[of])), default=0.0)
        if err > CROSS_TOL:
            raise ExactError(f"exact encoded state deviates from float by {err}")
        out.append({"codes": codes, "amps": amps})
    _ENC_CACHE[enc.name] = out
    return out


# --------------------------------------------------------------------------------------------------------------------
# Exact link operator U_ij (CG convention, jmax = 1/2)
def _exact_cg(j1, m1, j2, m2, J, M):
    """(S, q) with CG = S * sqrt(q), S and q rational (Racah's closed formula, Condon-Shortley phase); (0, 0) if zero."""
    two = lambda x: int(round(2 * x))  # noqa: E731
    if two(m1) + two(m2) != two(M) or two(J) < abs(two(j1) - two(j2)) or two(J) > two(j1) + two(j2):
        return Fraction(0), Fraction(0)
    if abs(two(m1)) > two(j1) or abs(two(m2)) > two(j2) or abs(two(M)) > two(J):
        return Fraction(0), Fraction(0)
    f = lambda x: math.factorial(int(round(x)))  # noqa: E731
    q = Fraction((two(J) + 1) * f(J + j1 - j2) * f(J - j1 + j2) * f(j1 + j2 - J), f(j1 + j2 + J + 1))
    q *= f(J + M) * f(J - M) * f(j1 - m1) * f(j1 + m1) * f(j2 - m2) * f(j2 + m2)
    s = Fraction(0)
    kmin = int(round(max(0, j2 - J - m1, j1 - J + m2)))
    kmax = int(round(min(j1 + j2 - J, j1 - m1, j2 + m2)))
    for k in range(kmin, kmax + 1):
        den = (f(k) * f(j1 + j2 - J - k) * f(j1 - m1 - k) * f(j2 + m2 - k) * f(J - j2 + m1 + k) * f(J - j1 - m2 + k))
        s += Fraction((-1) ** k, den)
    return s, q


@functools.lru_cache(maxsize=1)
def exact_link_U() -> list[list[list[list[KNum]]]]:
    """U[a][b][kp][k] (5 x 5 each, CG convention, LinkSpace(0.5) index order), exact; cross-checked vs LinkSpace.U()."""
    from su2plaq.su2.algebra import LinkSpace

    ls = LinkSpace(0.5)
    col = [0.5, -0.5]
    U = [[[[KNum(0) for _ in range(ls.dim)] for _ in range(ls.dim)] for _ in range(2)] for _ in range(2)]
    for (j, mL, mR), k in ls.index.items():
        for jp in ls.spins:
            if abs(jp - j) != 0.5:
                continue
            for a, ic in enumerate(col):
                for b, jc in enumerate(col):
                    mLp, mRp = mL + ic, mR + jc
                    if abs(mLp) > jp + 1e-9 or abs(mRp) > jp + 1e-9:
                        continue
                    kp = ls.index[(jp, mLp, mRp)]
                    s1, q1 = _exact_cg(0.5, ic, j, mL, jp, mLp)
                    s2, q2 = _exact_cg(0.5, jc, j, mR, jp, mRp)
                    if s1 == 0 or s2 == 0:
                        continue
                    q = Fraction(int(round(2 * j + 1)), int(round(2 * jp + 1))) * q1 * q2
                    U[a][b][kp][k] = U[a][b][kp][k] + sqrt_rational(q) * (s1 * s2)
    fl = ls.U()
    for a in range(2):
        for b in range(2):
            for kp in range(ls.dim):
                for k in range(ls.dim):
                    if abs(U[a][b][kp][k].to_complex() - fl[a][b][kp, k]) > CROSS_TOL:
                        raise ExactError("exact link operator deviates from float")
    return U


# --------------------------------------------------------------------------------------------------------------------
# Exact magnetic Hamiltonian on the physical basis and the exact targets
_INNER = 625


def _sparse_cols(M):
    """5x5 KNum matrix (M[row][col]) -> {col: [(row, val)]}."""
    out = {}
    for c in range(5):
        out[c] = [(r, M[r][c]) for r in range(5) if not M[r][c].is_zero()]
    return out


def _transpose_real(M):
    return [[M[c][r].conj() for c in range(5)] for r in range(5)]


def _plaquette_W_from_U(U) -> dict:
    """Sparse columns {col: {row: KNum}} of W = sum_{abce} U_l^dag(e,a) U_t^dag(c,e) U_r(b,c) U_b(a,b) on four links
    (index sum_l s_l 5^l, link 0 least significant), for the 2x2 array U of 5x5 KNum matrices."""
    cols = {}
    for c in range(_INNER):
        s = [(c // 5 ** l) % 5 for l in range(4)]          # s[0] = b, s[1] = r, s[2] = t, s[3] = l
        acc: dict = {}
        for a, b, cc, e in itertools.product(range(2), repeat=4):
            Ub, Ur = U[a][b], U[b][cc]
            Ut = _transpose_real(U[e][cc])
            Ul = _transpose_real(U[a][e])
            lists = [[(r, Ub[r][s[0]]) for r in range(5) if not Ub[r][s[0]].is_zero()],
                     [(r, Ur[r][s[1]]) for r in range(5) if not Ur[r][s[1]].is_zero()],
                     [(r, Ut[r][s[2]]) for r in range(5) if not Ut[r][s[2]].is_zero()],
                     [(r, Ul[r][s[3]]) for r in range(5) if not Ul[r][s[3]].is_zero()]]
            if not all(lists):
                continue
            for (rb, vb), (rr, vr), (rt, vt), (rl, vl) in itertools.product(*lists):
                row = rb + 5 * rr + 25 * rt + 125 * rl
                v = ((vb * vr) * (vt * vl))
                acc[row] = acc[row] + v if row in acc else v
        cols[c] = {r: v for r, v in acc.items() if not v.is_zero()}
    return cols


def _check_W(cols: dict, convention: str) -> None:
    from su2plaq.exact.operators import plaquette_W

    Wf = plaquette_W(convention=convention)
    err = 0.0
    for c, d in cols.items():
        colf = Wf[:, c].copy()
        for r, v in d.items():
            colf[r] -= v.to_complex()
        err = max(err, float(np.abs(colf).max()))
    if err > CROSS_TOL:
        raise ExactError(f"exact W ({convention}) deviates from float by {err}")


@functools.lru_cache(maxsize=1)
def exact_plaquette_W() -> dict:
    """W = Tr(U_b U_r U_t^dag U_l^dag) on the four inner links in the CG convention (index sum_l s_l 5^l, link 0 least
    significant) as a sparse column dict {col: {row: KNum}}; exact, cross-checked against the float W."""
    cols = _plaquette_W_from_U(exact_link_U())
    _check_W(cols, "cg")
    return cols


@functools.lru_cache(maxsize=1)
def exact_paulo_U() -> list:
    """Paulo's Eq. 28 link operators in the order (0, ++, +-, -+, --): U_ab|ab> = |0>/sqrt2, U_ab|0> = s(a)s(b)|a'b'>/sqrt2."""
    r = sqrt_rational(Fraction(1, 2))
    s = {0: 1, 1: -1}
    bar = {0: 1, 1: 0}
    idx = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
    U = [[[[KNum(0) for _ in range(5)] for _ in range(5)] for _ in range(2)] for _ in range(2)]
    for a in range(2):
        for b in range(2):
            U[a][b][0][idx[(a, b)]] = r
            U[a][b][idx[(bar[a], bar[b])]][0] = r * (s[a] * s[b])
    from su2plaq.su2.algebra import paulo_U

    fl = paulo_U()
    for a in range(2):
        for b in range(2):
            for i in range(5):
                for j in range(5):
                    if abs(U[a][b][i][j].to_complex() - fl[a][b][i, j]) > CROSS_TOL:
                        raise ExactError("exact Paulo link operator deviates from float")
    return U


@functools.lru_cache(maxsize=1)
def exact_plaquette_W_paulo() -> dict:
    cols = _plaquette_W_from_U(exact_paulo_U())
    _check_W(cols, "paulo")
    return cols


@functools.lru_cache(maxsize=1)
def exact_HB() -> dict:
    """H_B^phys = -(A + A^dag), A[k',k] = <psi_k'| W (x) 1 |psi_k>, exact (all real in K); {(k', k): KNum}; cross-checked."""
    basis = _exact_basis_cached("cg")
    W = exact_plaquette_W()
    inv: dict = {}
    for k, st in enumerate(basis):
        for key, a in zip(st["keys"], st["amps"]):
            inv.setdefault(int(key), []).append((k, a))
    A: dict = {}
    for k, st in enumerate(basis):
        wpsi: dict = {}
        for key, a in zip(st["keys"], st["amps"]):
            key = int(key)
            inner, outer = key % _INNER, key // _INNER
            for r, w in W[inner].items():
                kk = outer * _INNER + r
                v = a * w
                wpsi[kk] = wpsi[kk] + v if kk in wpsi else v
        for kk, v in wpsi.items():
            for kp, a2 in inv.get(kk, ()):
                t = (kp, k)
                val = a2.conj() * v
                A[t] = A[t] + val if t in A else val
    H: dict = {}
    for (kp, k), v in A.items():                      # H = -(A + A^dagger)
        for t, val in (((kp, k), -v), ((k, kp), -v.conj())):
            H[t] = H[t] + val if t in H else val
    H = {t: v for t, v in H.items() if not v.is_zero()}
    from su2plaq.exact.operators import h_magnetic_phys
    from su2plaq.exact.physical import physical_basis

    Hf, _ = h_magnetic_phys(physical_basis(convention="cg"))
    dense = np.zeros_like(Hf)
    for (i, j), v in H.items():
        dense[i, j] = v.to_complex()
    err = float(np.abs(dense - Hf).max())
    if err > CROSS_TOL:
        raise ExactError(f"exact H_B deviates from float by {err}")
    return H


def _components(n: int, H: dict) -> list[list[int]]:
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (i, j) in H:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    comp: dict = {}
    for i in range(n):
        comp.setdefault(find(i), []).append(i)
    return sorted(comp.values(), key=lambda c: c[0])


SPECTRUM = tuple(Fraction(x, 2) for x in (-4, -2, -1, 0, 1, 2, 4))   # lambda in {-2, -1, -1/2, 0, 1/2, 1, 2}


def _matmul(A, B):
    n = len(A)
    out = [[KNum(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for k in range(n):
            a = A[i][k]
            if a.is_zero():
                continue
            for j in range(n):
                b = B[k][j]
                if not b.is_zero():
                    out[i][j] = out[i][j] + a * b
    return out


def _poly_from_roots(roots: list[Fraction]) -> list[Fraction]:
    """Coefficients c_0..c_n of prod (x - r)."""
    c = [Fraction(1)]
    for r in roots:
        nc = [Fraction(0)] * (len(c) + 1)
        for i, v in enumerate(c):
            nc[i + 1] += v
            nc[i] -= r * v
        c = nc
    return c


def spectral_projectors(Hblk: list[list[KNum]]) -> dict[Fraction, list[list[KNum]]]:
    """Exact P_lambda = prod_{mu != lambda} (H - mu)/(lambda - mu) for lambda in SPECTRUM; raises ExactError unless
    prod_mu (H - mu) = 0 (i.e. the spectrum of the block lies in SPECTRUM)."""
    n = len(Hblk)
    ident = [[KNum(1) if i == j else KNum(0) for j in range(n)] for i in range(n)]
    pows = [ident]
    for _ in range(len(SPECTRUM)):
        pows.append(_matmul(pows[-1], Hblk))

    def combo(coefs):
        out = [[KNum(0) for _ in range(n)] for _ in range(n)]
        for p, cf in zip(pows, coefs):
            if cf == 0:
                continue
            for i in range(n):
                for j in range(n):
                    if not p[i][j].is_zero():
                        out[i][j] = out[i][j] + p[i][j] * cf
        return out

    full = combo(_poly_from_roots(list(SPECTRUM)))
    if any(not x.is_zero() for row in full for x in row):
        raise ExactError("a block of H_B has an eigenvalue outside {0, +-1/2, +-1, +-2}")
    res = {}
    for lam in SPECTRUM:
        coefs = _poly_from_roots([m for m in SPECTRUM if m != lam])
        den = Fraction(1)
        for m in SPECTRUM:
            if m != lam:
                den *= lam - m
        res[lam] = combo([c / den for c in coefs])
    return res


def target_base(kind: str, order: int = 1) -> tuple[int, int]:
    """(d_alpha, d_beta): theta_alpha = alpha/d_alpha, theta_beta = beta/d_beta of `exact_target_blocks`."""
    return (8 if (kind == "step" and order == 2) else 4, 2)


@functools.lru_cache(maxsize=1)
def _beta_blocks() -> tuple:
    """Blocks of H_B (connected components) with the exact projector decomposition: [(ks, {lambda: P_lambda})]."""
    basis = _exact_basis_cached("cg")
    H = exact_HB()
    comps = _components(len(basis), H)
    out = []
    for ks in comps:
        pos = {k: i for i, k in enumerate(ks)}
        Hb = [[KNum(0) for _ in ks] for _ in ks]
        for (i, j), v in H.items():
            if i in pos:
                Hb[pos[i]][pos[j]] = v
        out.append((ks, spectral_projectors(Hb)))
    return tuple(out)


def _n_electric(k: int) -> int:
    lab = _exact_basis_cached("cg")[k]["label"]
    return sum(1 for j in lab[0][:4] if j == 0.5)


_TGT_CACHE: dict = {}


def exact_target_blocks(kind: str, order: int = 1) -> list[dict]:
    """Exact target in blocks: [{"ks": [...], "entries": [(i, j, Laurent)]}] with V[ks[i], ks[j]] a Laurent polynomial in
    (z_alpha, z_beta), base (d_alpha, d_beta) = target_base(kind, order): U_E = diag(z_alpha^{-3 n}) (n = number of inner links
    with j = 1/2), U_B = sum_lambda P_lambda z_beta^{-2 lambda}, step = U_B U_E (order 1) or U_E(alpha/2) U_B U_E(alpha/2)
    (order 2, d_alpha = 8).  Cross-checked against `operators.target` at (0.37, 0.61) (<= 1e-12 per entry)."""
    if kind not in ("UE", "UB", "step"):
        raise ValueError(f"unknown kind {kind!r}")
    if kind == "step" and order not in (1, 2):
        raise ValueError(f"order must be 1 or 2, got {order}")
    key = (kind, order if kind == "step" else 1)
    if key in _TGT_CACHE:
        return _TGT_CACHE[key]
    basis = _exact_basis_cached("cg")
    nel = [_n_electric(k) for k in range(len(basis))]
    blocks = []
    if kind == "UE":
        for k in range(len(basis)):
            blocks.append({"ks": [k], "entries": [(0, 0, Laurent.mono((-3 * nel[k], 0), K_ONE))]})
    else:
        for ks, proj in _beta_blocks():
            ents = []
            for i, ki in enumerate(ks):
                for j, kj in enumerate(ks):
                    lp = Laurent()
                    for lam, P in proj.items():
                        if not P[i][j].is_zero():
                            lp = lp + Laurent.mono((0, int(-2 * lam)), P[i][j])
                    if lp:
                        if kind == "step":
                            # order 1: U_B U_E, exponent -3 n_j (units alpha/4); order 2: U_E(a/2) U_B U_E(a/2),
                            # exponent -3 (n_i + n_j) (units alpha/8)
                            e = (-3 * nel[kj], 0) if order == 1 else (-3 * (nel[ki] + nel[kj]), 0)
                            lp = lp.shift(e)
                        ents.append((i, j, lp))
            blocks.append({"ks": list(ks), "entries": ents})
    # float cross-check
    from su2plaq.exact.operators import target as ftarget
    from su2plaq.exact.physical import physical_basis

    al, be = 0.37, 0.61
    dA, dB = target_base(kind, order)
    Vf = ftarget(physical_basis(convention="cg"), kind, al, be, order)
    Vd = np.zeros_like(Vf)
    for blk in blocks:
        ks = blk["ks"]
        for i, j, lp in blk["entries"]:
            Vd[ks[i], ks[j]] = lp.evaluate(al / dA, be / dB)
    err = float(np.abs(Vd - Vf).max())
    if err > CROSS_TOL:
        raise ExactError(f"exact {kind} target deviates from float by {err}")
    _TGT_CACHE[key] = blocks
    return blocks
