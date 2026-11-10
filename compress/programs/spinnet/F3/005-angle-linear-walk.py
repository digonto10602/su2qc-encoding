"""SUMMARY: angle-linear form of the F3 parent (Na=NOR(c0,c1) ancilla, A=[u=v=0] in place in c1, Nd=NOR(c2,c3) direct rccx pair + CZ(Na,c2); 9-term walk e -> 0, 32 CX, 17 qubits, 9+4 rotations): every rotation angle is exactly k*beta/4 or -3*alpha/4 (no pi/4 offsets and no fused pi/2 offsets; s/sdg are separate gates), so the circuit is angle-linear (Lean exporter ok) at an unchanged skeleton; robust key (32, 16948, 0, 33225, 17) vs parent (32, 16954, 1).
DISCOVERY: free sign tools for direct rccx pairs: two Z on the pivot at steps i<j give (-1)^(g_i^g_j) (incl. direct flags), a CZ fused into a toggle (sdg(0) cx(x,0) s(0) s(x), 1 CX) twice on one atom gives (-1)^(x(g_i^g_j)), rccx literal pairs (ab, abar bbar)/(abar b, a bbar) leave only S phases, and the AND toggle ch(a,P) cz(b,P) ch(a,P) (3 CX, 4 T) leaves (-1)^(abar b dS) instead of (-1)^(a dS); none fixes the leftover (-1)^(c2bar Na) of the 6 nine-toggle walks of the parent design (exhaustive over 7 linear toggles, free ends span(e,u), all four second-toggle variants), so 32 CX stays.
DISCOVERY: with A in an ancilla and BOTH corner NORs toggled by crossing direct rccx pairs, 9-rotation walks need only 5 linear toggles (8 walks per pairing, 29 CX before the sign fix; 88 walks with 6), but the leftover is ~[corner x only] ^ [corner y only] (x, y one corner of each pair) and is not in the span of the free tools plus any two CZ products of wire values (corners x links included), so the design costs >= 32 CX.
DISCOVERY: the robust T sum is set by the rotation count (about 63 T per rotation at random angles): removing the pi/4 offsets of r04-F3-004 changes the 20-pair sum only 16954 -> 16948 but makes the circuit angle-linear (Lean exporter ok); only a 31-CX circuit with <= 12 walk rotations can beat the 31-CX, 17-rotation headline.
"""
FAMILY = "F3"
PARENT = "r04-F3-004"

import dataclasses

import numpy as np

from su2plaq.compress import oracle
from su2plaq.compress.builder import Builder

# Wires (F3 ladder frame): q0 pivot (b), q1 e=b^r, q2 u=b^t, q3 v=r^l, q4..q7 corners c0..c3, ancilla Na.
QI = {"e": 1, "u": 2, "v": 3, "c0": 4, "c1": 5, "c2": 6, "c3": 7}
# AND flags, computed in this order and uncomputed in reverse: (target, (control, negated), (control, negated)).
FLAGS = [("Na", ("c0", 1), ("c1", 1)),      # Na = NOR(c0, c1) in a clean ancilla
         ("c1", ("u", 1), ("v", 1))]        # c1 ^= A with A = [u=v=0]; c1 is idle until Na is uncomputed
S0 = "e"                                     # free preload of e (fused with the last ladder CX)
ND = (("c2", 1), ("c3", 1))                 # Nd = NOR(c2, c3) toggled onto the pivot by rccx, first control c2bar
# Walk steps: (kind, wire or ND, frame flip).  A flip on a CX step is a negated control (x on the control wire),
# on an rccx step an x(0) before it and a z on its first control after it.
WALK = [("cx", "c1", 0), ("cx", "e", 0), ("and", ND, 0), ("cx", "c1", 0), ("cx", "Na", 1),
        ("cx", "c1", 1), ("and", ND, 0), ("cx", "c1", 0), ("cx", "Na", 1)]
TRANSIT = {2}                                # visit 2 (= c1^A alone) carries no rotation
FIX = [("cz", "Na", "c2"), ("z", "Na")]      # the Nd rccx pair leaves (-1)^(c2bar * Na)


def _codes(spec):
    """Data code (bits 0..7) of every physical state, from the oracle codec."""
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


def _lit(w, c):
    return w[c[0]] ^ c[1]


def _trace(d):
    """Pivot value after the preload and after every walk step (frame flips excluded), for data code d."""
    b, r, t, l = [(d >> i) & 1 for i in range(4)]
    w = {"e": b ^ r, "u": b ^ t, "v": r ^ l}
    for k in range(4):
        w[f"c{k}"] = (d >> (4 + k)) & 1
    for tgt, c1, c2 in FLAGS:
        w[tgt] = w.get(tgt, 0) ^ (_lit(w, c1) & _lit(w, c2))
    g = w[S0]
    seq = [g]
    for kind, x, _ in WALK:
        g ^= w[x] if kind == "cx" else (_lit(w, x[0]) & _lit(w, x[1]))
        seq.append(g)
    return w, seq


def _snap(x, den=64):
    """Snap to the exact rational k/den (Lean-certifiable angles); refuses anything else."""
    x = np.asarray(x, float)
    k = np.round(x * den)
    assert np.abs(x * den - k).max() < 1e-8, "coefficient is not a multiple of 1/64"
    return k / den


def _weights(spec, codes):
    """f = K on the bright pairs (oracle), 0 on dark codes; solve f = sum_i w_i (-1)^{g_i} over the rotated visits."""
    b0 = 0.25
    ub = oracle.target(dataclasses.replace(spec, kind="UB", beta=b0))
    index = {c: i for i, c in enumerate(codes)}
    rows, tv = [], []
    for i, ci in enumerate(codes):
        d = ci & 255
        if (d >> 4) == 0:
            val = float(np.arctan2(-ub[index[ci ^ 0b1111], i].imag, ub[i, i].real)) / b0
        else:
            assert abs(ub[i, i] - 1) < 1e-12
            val = 0.0
        rows.append(_trace(d)[1])
        tv.append(val)
    rows = np.array(rows)
    cols = [k for k in range(len(WALK) + 1) if k not in TRANSIT]
    X = (1 - 2 * rows[:, cols]).astype(float)
    w, *_ = np.linalg.lstsq(X, np.array(tv), rcond=None)
    assert np.abs(X @ w - np.array(tv)).max() < 1e-10, "walk does not represent K"
    return dict(zip(cols, _snap(w)))


def _rccx(b, q, c1, c2, t):
    for c in (c1, c2):
        if c[1]:
            b.x(q[c[0]])
    b.rccx(q[c1[0]], q[c2[0]], t)
    for c in (c1, c2):
        if c[1]:
            b.x(q[c[0]])


def build(spec):
    b = Builder(spec)
    (na,) = b.alloc(1, "flag")
    q = dict(QI)
    q["Na"] = na
    codes = _codes(spec)
    wts = _weights(spec, codes)
    ends = {(_trace(ci & 255)[1][-1]) for ci in codes}
    assert len(ends) == 1
    zend = ends.pop() ^ (sum(f for _, _, f in WALK) & 1)
    # ---- U_E: p(lam) on every link, lam = -3 alpha / 4 (solved from the oracle and snapped to k/64)
    ue = oracle.target(dataclasses.replace(spec, kind="UE", alpha=0.25))
    nl = np.array([bin(c & 15).count("1") for c in codes], float)
    ph = -np.angle(np.diag(ue)) / 0.25
    ce = float(np.dot(nl, ph) / np.dot(nl, nl))
    assert np.abs(nl * ce - ph).max() < 1e-10
    lam = -float(_snap([ce])[0]) * spec.alpha
    for k in range(4):
        b.p(lam, k)
    # ---- ladder q3 = v, q2 = u, q1 = e; cx(0,1) h(0) cx(1,0) [preload e] = sdg(1) cx(0,1) s(1) s(0) h(0)
    b.cx(1, 3)
    b.cx(0, 2)
    b.sdg(1)
    b.cx(0, 1)
    b.s(1)
    b.s(0)
    b.h(0)
    for tgt, c1, c2 in FLAGS:
        _rccx(b, q, c1, c2, q[tgt])
    beta = spec.beta
    frame = 0

    def rot(k):
        if wts.get(k, 0) != 0:
            b.rz(2.0 * float(wts[k]) * beta * (-1) ** frame, 0)
    rot(0)
    for k, (kind, x, flip) in enumerate(WALK, start=1):
        if kind == "cx":
            if flip:
                b.x(q[x])
            b.cx(q[x], 0)
            if flip:
                b.x(q[x])
        else:
            if flip:
                b.x(0)
            _rccx(b, q, x[0], x[1], 0)
            if flip:
                b.z(q[x[0][0]])
        frame ^= flip
        rot(k)
    for g in FIX:
        if g[0] == "cz":
            b.cz(q[g[1]], q[g[2]])
        else:
            getattr(b, g[0])(q[g[1]])
    for tgt, c1, c2 in reversed(FLAGS):
        _rccx(b, q, c1, c2, q[tgt])
    # ---- inverse ladder (walk ends at parity 0)
    b.h(0)
    b.cx(0, 1)
    b.cx(0, 2)
    b.cx(1, 3)
    if zend:
        b.z(0)
    b.free([na])
    return b
