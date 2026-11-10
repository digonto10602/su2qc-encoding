"""SUMMARY: searched U_B (scratch/proposer/f3): flags A=[u=v=0], NOR(c0,c1), NOR(c2,c3) (3 rccx pairs), a 9-term pivot phase polynomial (MILP enumeration + exact free-endpoint TSP: 9 pivot CX), and the final CX(e,p) unload fused with the ladder tail into one 2-CX Clifford; 33 CX, 13 rotations, angles k*beta/4 and -3*alpha/4 solved from the oracle and snapped to k/64.
DISCOVERY: the ladder Clifford [CX(0,2) CX(0,1) H(0)] absorbs any pivot preload/unload from span(e,u) for free (3-qubit block CX(e->p) H CX(0,1) CX(0,2) = 2 CX), so the pivot walk may start/end at p, p^e, p^u, p^e^u at no cost.
DISCOVERY: with flags A, NOR(c0,c1), NOR(c2,c3) the minimal pivot polynomial has exactly 9 terms (10 solutions) and needs 9 pivot CX; the pair NOR(c0,c2),NOR(c1,c3) (the pairs9 seed) also reaches 9 with free endpoints.
DISCOVERY: single flag A gives 16 terms, but no parity network below 22 CX was found (beam/TSP/annealing over all 624 minimal sets), so 34 CX is that family's floor in this search.
"""
FAMILY = "F3"
PARENT = None

import dataclasses

import numpy as np

from su2plaq.compress import oracle
from su2plaq.compress.builder import Builder

# Pivot walk in the H frame of the pivot q0: each entry is the control wire of CX(control -> q0).
# Wires: "F2" = NOR(c2,c3), "A" = [u=v=0], "F1" = NOR(c0,c1), "e" = b^r on q1.
WALK = ["F2", "A", "F1", "A", "F2", "A", "F1", "e", "A"]
# Terms of the pivot polynomial (sets of wires multiplying Z_p); the walk visits each of them once.
TERMS = [frozenset(), frozenset({"F2"}), frozenset({"A", "F2"}), frozenset({"A", "F1", "F2"}), frozenset({"F1", "F2"}),
         frozenset({"F1"}), frozenset({"A", "F1"}), frozenset({"A", "e"}), frozenset({"e"})]
_A0 = 0.25  # reference angles for reading the angle-independent generators (K and the electric weight) from the oracle
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


def _wires(code):
    """Values of the walk wires for a data code (after the ladder and the flags)."""
    b, r, t, l = [(code >> i) & 1 for i in range(4)]
    c = [(code >> (4 + k)) & 1 for k in range(4)]
    u, v = b ^ t, r ^ l
    return {"e": b ^ r, "A": int(u == 0 and v == 0), "F1": int(c[0] == 0 and c[1] == 0), "F2": int(c[2] == 0 and c[3] == 0)}


def _coefficients(spec, codes):
    """Pivot polynomial f(wires) with exp(-i beta f X_pivot) = U_B on every valid data code: f = K on the bright pairs
    (read from the oracle), f = 0 on dark codes.  Least squares over the term characters; must be exact."""
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
        key = tuple(sorted(_wires(d).items()))
        assert key not in f or abs(f[key] - val) < 1e-9
        f[key] = val
    keys = sorted(f)
    W = np.array([[(-1) ** sum(dict(k)[w] for w in T) for T in TERMS] for k in keys], float)
    t = np.array([f[k] for k in keys])
    w, *_ = np.linalg.lstsq(W, t, rcond=None)
    assert np.abs(W @ w - t).max() < 1e-10, "term set does not represent K"
    return _snap(w)


def _snap(x, den=64):
    """Snap solved coefficients to the exact rational k/den they equal (Lean-certifiable angles); refuses otherwise."""
    x = np.asarray(x, float)
    k = np.round(x * den)
    assert np.abs(x * den - k).max() < 1e-8, "coefficient is not a multiple of 1/64"
    return k / den


def build(spec):
    b = Builder(spec)
    fA, f1, f2 = b.alloc(3, "flags")
    wire = {"A": fA, "F1": f1, "F2": f2, "e": 1}
    codes = _codes(spec)
    # electric layer: -arg(U_E)/alpha = cE * (number of j=1/2 inner links), cE read from the oracle (= 3/4)
    ue = oracle.target(dataclasses.replace(spec, kind="UE", alpha=_A0))
    nl = np.array([bin(c & 15).count("1") for c in codes], float)
    ph = -np.angle(np.diag(ue)) / _A0
    cE = float(np.dot(nl, ph) / np.dot(nl, nl))
    assert np.abs(nl * cE - ph).max() < 1e-10
    cE = float(_snap([cE])[0])
    for k in range(4):
        b.p(-cE * spec.alpha, k)
    w = _coefficients(spec, codes)
    coef = dict(zip(TERMS, w))
    # ladder: q1 = e = b^r, q2 = u = b^t, q3 = v = r^l, pivot q0 = b (X^{x4} on the links -> X on q0), then H on the pivot
    b.cx(1, 3)
    b.cx(0, 2)
    b.cx(0, 1)
    b.h(0)
    # flags (relative-phase Toffolis; RCCX^2 = I and the walk is diagonal, so the phases cancel)
    flag_gates = [((2, 3), fA), ((4, 5), f1), ((6, 7), f2)]
    for (a, c), t in flag_gates:
        b.x(a)
        b.x(c)
        b.rccx(a, c, t)
        b.x(a)
        b.x(c)
    # pivot walk: rz(2 beta f_T) on the pivot whenever its parity is a term (first visit)
    par = frozenset()
    done = set()

    def rot():
        if par in coef and par not in done:
            b.rz(2.0 * coef[par] * spec.beta, 0)
            done.add(par)
    rot()
    for ctl in WALK:
        b.cx(wire[ctl], 0)
        par = par ^ {ctl}
        rot()
    assert done == set(TERMS) and par == frozenset({"e"})
    for (a, c), t in reversed(flag_gates):
        b.x(c)
        b.x(a)
        b.rccx(a, c, t)
        b.x(c)
        b.x(a)
    # fused tail: CX(1,0) [unload e from the pivot] . H(0) . CX(0,1) . CX(0,2) as one 2-CX Clifford (qiskit synth_clifford_bm)
    b.x(0)
    b.h(0)
    b.s(0)
    b.h(1)
    b.s(1)
    b.cx(0, 2)
    b.cx(0, 1)
    b.sdg(1)
    b.h(1)
    b.cx(1, 3)
    b.free([fA, f1, f2])
    return b
