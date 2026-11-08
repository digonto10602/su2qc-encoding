"""SUMMARY: F3 searched walk with one direct AND: clean flags A=[u=v=0], N2=NOR(c2,c3); N1=NOR(c0,c1) toggled straight onto the pivot by two rccx (CZ(c0,N2) cancels their leftover sign); 9-term pivot walk from the free preload e to 0 with 7 cheap toggles; pivot sign flips carried by negated toggle controls and p(lam+-pi/2) electric angles pick the shorter Clifford+T words; 32 CX, 9+4 rotations k*beta/4, 3*alpha/4 (+-pi/2).
DISCOVERY: with A=[u=v=0] the only consistent 2-AND companions are the three corner NOR pairings, and every minimal 9-term polynomial is the (A,N1,N2) cube minus one vertex A.X plus {X.e', X.e'.A} (e' in e+span(u,v)) with X.e'.A a dead end: no 8-toggle walk (33 CX all-ancilla, 32 with one direct AND + 1 CZ); a term-set-free DFS (f in span of the visited parities) finds no 31-CX walk with one direct AND (any pairing or flag), N1+N2 direct (all pairings) or A+N1 direct (pairing 01|23).
DISCOVERY: the leftover sign (-1)^(ck_bar*dS) of a direct rccx pair with first control ck_bar is free exactly when dS is constant on c_k=1 states (corner rule): dS in {0, e^v} for c0, {0, e} for c1, {0, e^u} for c2, {0, e^u^v} for c3 (plus affine terms); no minimal walk reaches it, hence the CZ.
DISCOVERY: gridsynth word length (not T) depends on the sign and pi/2 shift of the angle (beta=0.61: +beta/4 140 gates, -beta/4 167; -beta/2 166, +beta/2 171); pivot sign flips done by x on a toggle's control wire (off the critical path) and p(lam+-pi/2) with the s/sdg absorbed by the ladder cut depth_CT 1585 -> 1553 at equal CX and T.
"""
FAMILY = "F3"
PARENT = "r01-F3-001"

import dataclasses

import numpy as np

from su2plaq.compress import oracle
from su2plaq.compress.builder import Builder

# Key bits of the pivot parity: 0 e (q1), 3 A (ancilla), 4 N1 (direct), 5 N2 (ancilla).
E, AB, N1B, N2B = 1, 8, 16, 32
S0 = E                      # free preload of e, fused with the last ladder CX
# Walk: (toggled key bit, negated control).  A negated control toggles NOT(x) = x plus a pivot flip, which flips the sign
# of every later rotation; the flips are placed so that each rotation angle is the one with the shorter word.
WALK = [(AB, 0), (E, 0), (N1B, 0), (AB, 0), (N2B, 1), (AB, 1), (N1B, 0), (AB, 0), (N2B, 1)]
_A0 = 0.25
_B0 = 0.25


def _codes(spec):
    """Data code (bits 0..7) of every physical state, read from the oracle codec."""
    out = []
    k = 0
    while True:
        try:
            txt = oracle.codec(spec, k)
        except IndexError:
            break
        line = [ln for ln in txt.splitlines() if ln.startswith("  ") and "j" in ln][-1].split()
        out.append(int(line[0], 2))
        k += 1
    return out


def _bits(d):
    """Wire values of data code d in the ladder frame: e, u, v, corners, flags."""
    b, r, t, l = [(d >> i) & 1 for i in range(4)]
    c = [(d >> (4 + k)) & 1 for k in range(4)]
    e, u, v = b ^ r, b ^ t, r ^ l
    A = int(u == 0 and v == 0)
    N1 = int(c[0] == 0 and c[1] == 0)
    N2 = int(c[2] == 0 and c[3] == 0)
    return dict(b=b, r=r, t=t, l=l, c=c, e=e, u=u, v=v, A=A, N1=N1, N2=N2,
                key=e | (u << 1) | (v << 2) | (A << 3) | (N1 << 4) | (N2 << 5))


def _par(mask, key):
    return bin(mask & key).count("1") & 1


def _snap(x, den=64):
    """Snap solved coefficients to the exact rational k/den they equal (Lean-certifiable angles); refuses otherwise."""
    x = np.asarray(x, float)
    k = np.round(x * den)
    assert np.abs(x * den - k).max() < 1e-8, "coefficient is not a multiple of 1/64"
    return k / den


def _visits():
    """Pivot parity (key mask, constant flip) after the preload and after every toggle."""
    cur, cst = S0, 0
    seq = [(cur, cst)]
    for bit, neg in WALK:
        cur ^= bit
        cst ^= neg
        seq.append((cur, cst))
    return seq


def _terms(seq):
    """Terms of the pivot polynomial = parities visited (A alone is a transit, not a term)."""
    out = []
    for m, _ in seq:
        if m != AB and m not in out:
            out.append(m)
    return out


def _coefficients(spec, codes, terms):
    """f(wires) with exp(-i beta f X_pivot) = U_B on every valid data code: f = K on the bright pairs (oracle), 0 on dark
    codes; least squares over the term characters, required exact."""
    ub = oracle.target(dataclasses.replace(spec, kind="UB", beta=_B0))
    index = {c: i for i, c in enumerate(codes)}
    f = {}
    for i, ci in enumerate(codes):
        d = ci & 255
        if (d >> 4) == 0:
            j = index[ci ^ 0b1111]
            val = float(np.arctan2(-ub[j, i].imag, ub[i, i].real)) / _B0
        else:
            assert abs(ub[i, i] - 1) < 1e-12
            val = 0.0
        key = _bits(d)["key"]
        assert key not in f or abs(f[key] - val) < 1e-9
        f[key] = val
    keys = sorted(f)
    W = np.array([[(-1) ** _par(T, k) for T in terms] for k in keys], float)
    t = np.array([f[k] for k in keys])
    w, *_ = np.linalg.lstsq(W, t, rcond=None)
    assert np.abs(W @ w - t).max() < 1e-10, "term set does not represent K"
    return dict(zip(terms, _snap(w)))


def _residual_ok(codes, seq):
    """Leftover sign of the two direct rccx(c0bar, c1bar -> pivot): (-1)^(N1 + c0bar * (P1 ^ P2)) with P_i the pivot parity
    after each of them (constant flips included).  Check that CZ(c0, N2) . Z(N2) . Z-gates listed below cancel it."""
    after = [s for (bit, _), s in zip(WALK, seq[1:]) if bit == N1B]
    assert len(after) == 2
    for ci in codes:
        x = _bits(ci & 255)
        a = 1 - x["c"][0]
        p = (_par(after[0][0], x["key"]) ^ after[0][1]) ^ (_par(after[1][0], x["key"]) ^ after[1][1])
        h = (x["N1"] + a * p) & 1
        fix = (x["c"][0] & x["N2"]) ^ x["N2"]
        assert h == fix, "residual sign is not cancelled by CZ(c0, N2) Z(N2)"


def build(spec):
    b = Builder(spec)
    fA, f2 = b.alloc(2, "flags")
    codes = _codes(spec)
    # electric layer: -arg(U_E)/alpha = cE * (number of j=1/2 inner links), cE read from the oracle (= 3/4)
    ue = oracle.target(dataclasses.replace(spec, kind="UE", alpha=_A0))
    nl = np.array([bin(c & 15).count("1") for c in codes], float)
    ph = -np.angle(np.diag(ue)) / _A0
    cE = float(np.dot(nl, ph) / np.dot(nl, nl))
    assert np.abs(nl * cE - ph).max() < 1e-10
    lam = -float(_snap([cE])[0]) * spec.alpha
    # p(lam) on every link; written as p(lam +- pi/2) and an s/sdg that is absorbed in the ladder Clifford (q0, q1)
    # or kept (q2, q3): the shifted angles have shorter Clifford+T words (same T count).
    b.p(lam + np.pi / 2, 0)            # = p(lam) . s(0); the s(0) of the fused ladder block below
    b.p(lam - np.pi / 2, 1)            # = p(lam) . sdg(1); the sdg(1) of the fused ladder block below
    b.p(lam + np.pi / 2, 2)
    b.sdg(2)
    b.p(lam + np.pi / 2, 3)
    b.sdg(3)
    seq = _visits()
    terms = _terms(seq)
    coef = _coefficients(spec, codes, terms)
    _residual_ok(codes, seq)
    # ladder q3 = v = r^l, q2 = u = b^t, then cx(0,1) h(0) cx(1,0) [preload e] = sdg(1) cx(0,1) s(1) s(0) h(0)
    b.cx(1, 3)
    b.cx(0, 2)
    b.cx(0, 1)
    b.s(1)
    b.h(0)
    # clean flags A = [u=0][v=0], N2 = [c2=0][c3=0]
    for q in (2, 3, 6, 7):
        b.x(q)
    b.rccx(2, 3, fA)
    b.rccx(6, 7, f2)
    for q in (2, 3, 6, 7):
        b.x(q)
    done = set()

    def rot(m, cst):
        if m in coef and m not in done:
            b.rz(2.0 * float(coef[m]) * spec.beta * (-1) ** cst, 0)
            done.add(m)
    rot(*seq[0])
    wire = {AB: fA, N2B: f2, E: 1}
    for (bit, neg), st in zip(WALK, seq[1:]):
        if bit == N1B:
            assert not neg
            b.x(4)
            b.x(5)
            b.rccx(4, 5, 0)                # N1 = [c0=0][c1=0] toggled straight onto the pivot
            b.x(5)
            b.x(4)
        else:
            q = wire[bit]
            if neg:
                b.x(q)
            b.cx(q, 0)
            if neg:
                b.x(q)
        rot(*st)
    assert done == set(terms)
    end, cst = seq[-1]
    assert end == 0
    # cancel the leftover sign of the rccx pair: (-1)^(c0bar * N2) = CZ(c0, N2) Z(N2)
    b.cz(4, f2)
    b.z(f2)
    for q in (6, 7, 2, 3):
        b.x(q)
    b.rccx(6, 7, f2)
    b.rccx(2, 3, fA)
    for q in (6, 7, 2, 3):
        b.x(q)
    # inverse ladder (the walk ends at parity 0 with one constant flip: x(0) h(0) = h(0) z(0))
    b.h(0)
    b.cx(0, 1)
    b.cx(0, 2)
    b.cx(1, 3)
    if cst:
        b.z(0)
    b.free([fA, f2])
    return b
