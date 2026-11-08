"""SUMMARY: F3 one-direct-AND walk on 17 qubits: Na=NOR(c0,c1) in the only ancilla, A=[u=v=0] XORed in place into c1 (idle between the Na compute and uncompute), Nd=NOR(c2,c3) toggled straight onto the pivot by two rccx (CZ(Na,c2) Z(Na) cancels their sign); 9-term walk e -> 0 with 7 cheap toggles, the one walk whose rotations all reach the shortest Clifford+T word (pivot X-frame flips by negated toggle controls only: sum of words 1358 = floor over all 32-CX walks); 32 CX, 9+4 rotations k*beta/8, 3*alpha/4 (+-pi/2).
DISCOVERY: no circuit below 32 CX (nor 31 CX with < 13 walk rotations) in: 3-AND walks with one direct AND plus raw corners c0..c3 as toggles; flags XORed in place into e/u/v or into the other flag's ancilla (breaks the bipartite parity of the 9-term walk, still no 8-toggle walk); A in a direct AND's control wire (rccx fusion); A direct + both NORs hosted; A + one opposite-corner NOR direct + linear corners (5794 walks of cost 19, none with a free sign); two-flag all-linear walks with 12 toggles.
DISCOVERY: gridsynth T of rz(k beta/8) at beta=0.61 depends only on |k| (k=2: 62, 4: 66, 6: 60, 8: 64; signs and pi/2 shifts change only the word length), and every 31-CX two-flag walk has weights {1/2, 4x1/4, 3x1/8, 5x3/8} (T_walk 814), every 32-CX three-flag walk {1/4, 5x3/8, 3x1/8} (T_walk 552): T at fixed CX is set by the term structure, not the walk.
DISCOVERY: a pivot X-frame flip across a direct rccx costs x(0) before it and z on its first control after it (x(t) rccx(~a,~b,t) z(a) = rccx(~a,~b,t) x(t) up to phase), so every rotation sign is free; the shortest words (1/8: 141 gates for +, 1/4: 170 for -, 3/8: 153) are all met by the walk A e Nd A Na A Nd A Na with flips on the two Na toggles.
"""
FAMILY = "F3"
PARENT = "r02-F3-002"

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
# on an rccx step an x(0) before it and a z on its first control after it; flips change the sign of later rotations
# (chosen so that +1/8 and -1/4 terms get the shorter Clifford+T words).
WALK = [("cx", "c1", 0), ("cx", "e", 0), ("and", ND, 0), ("cx", "c1", 0), ("cx", "Na", 1),
        ("cx", "c1", 1), ("and", ND, 0), ("cx", "c1", 0), ("cx", "Na", 1)]
TRANSIT = {2}                                # visit 2 (= c1^A alone) carries no rotation
SHIFT = {}                                   # rz(theta) = rz(theta + k pi/2) . sdg^k  (shorter word, same T)
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
    """Pivot value (incl. constants, frame flips excluded) after the preload and after every walk step, for data code d."""
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
    # the walk must end on parity 0 (constant allowed); its sign becomes a z(0) after the frame H
    ends = {(_trace(ci & 255)[1][-1]) for ci in codes}
    assert len(ends) == 1
    zend = ends.pop() ^ (sum(f for _, _, f in WALK) & 1)
    # ---- U_E: p(lam) on every link, lam = -3 alpha / 4 (oracle-checked); q0/q1 take the s(0)/sdg(1) of the fused
    # ladder block, q2/q3 a compensating sdg: the shifted angles have shorter Clifford+T words (same T)
    ue = oracle.target(dataclasses.replace(spec, kind="UE", alpha=0.25))
    nl = np.array([bin(c & 15).count("1") for c in codes], float)
    ph = -np.angle(np.diag(ue)) / 0.25
    ce = float(np.dot(nl, ph) / np.dot(nl, nl))
    assert np.abs(nl * ce - ph).max() < 1e-10
    lam = -float(_snap([ce])[0]) * spec.alpha
    b.p(lam + np.pi / 2, 0)            # p(lam) . s(0)
    b.p(lam - np.pi / 2, 1)            # p(lam) . sdg(1)
    b.p(lam + np.pi / 2, 2)
    b.sdg(2)
    b.p(lam + np.pi / 2, 3)
    b.sdg(3)
    # ---- ladder q3 = v, q2 = u, q1 = e; cx(0,1) h(0) cx(1,0) [preload e] = sdg(1) cx(0,1) s(1) s(0) h(0)
    b.cx(1, 3)
    b.cx(0, 2)
    b.cx(0, 1)
    b.s(1)
    b.h(0)
    for tgt, c1, c2 in FLAGS:
        _rccx(b, q, c1, c2, q[tgt])
    beta = spec.beta
    frame = 0

    def rot(k):
        if wts.get(k, 0) != 0:
            sh = SHIFT.get(k, 0)
            b.rz(2.0 * float(wts[k]) * beta * (-1) ** frame + sh * np.pi / 2, 0)
            for _ in range(sh):
                b.sdg(0)
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
