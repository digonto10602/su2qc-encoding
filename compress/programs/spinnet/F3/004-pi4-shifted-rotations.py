"""SUMMARY: F3 parent circuit (Na=NOR(c0,c1) ancilla, A=[u=v=0] in place in c1, Nd=NOR(c2,c3) direct rccx pair + CZ(Na,c2); 9-term walk e -> 0, 32 CX, 17 qubits) with every rotation that has a cheaper pi/4-shifted Clifford+T form emitted as p/rz(theta + pi/4) . tdg: the 4 electric p(-3alpha/4 +- pi/2) go 64 -> 58+1 T and the rz(+-beta/2) walk term 66 -> 64+1 (fixed decision, same skeleton at all angles); T 832 -> 811, angles k*beta/8, 3*alpha/4 (+ multiples of pi/4).
DISCOVERY: every crossing of two direct rccx pairs on the pivot (A with a corner NOR, or two corner NORs; all 3 pairings, 4 literal variants each, both first controls, all 7 crossing patterns of three direct units) leaves a sign that is cubic in the corners in sector e=u=v=0 and cannot be fixed with <= 2 CZ; nested or sequential direct pairs confine the walk to 3 of the 4 flag classes and the time-limited MILP finds no support below 13 terms (16 for most pairings, 14-30 for A+NOR direct) while 31 CX would need <= 12, so double/triple direct AND designs do not reach 31 CX (MILP values are incumbents, not proven optima).
DISCOVERY: hosting a corner NOR in the e wire (so that the fused ladder block would unload it for free) ties it to e: f leaves the span without raw corners and needs 25-30 terms with them; Na XORed into the first-control corner of the direct NOR (so that its enclosed toggle would cancel the rccx sign) needs >= 17 terms; dropping A and using only two corner NORs needs 14 terms (no 32-CX all-ancilla walk for pairing 01|23).
DISCOVERY: the star ladder CX(0,1) CX(0,2) CX(0,3) H(0) absorbs a pivot preload from any subset of q1..q3 (H(0) CX(k,0) = CZ(k,0) H(0) and each CX(0,k) CZ(0,k) is a 1-CX Clifford), so its free walk ends are all of span(b^r, b^t, b^l); it does not help here because A=[u=v=0] needs v=r^l on a wire, which the star frame lacks.
"""
FAMILY = "F3"
PARENT = "r03-F3-003"

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
    # each p(theta) is emitted as p(theta + pi/4) . tdg (exact): gridsynth needs 58 + 1 instead of 64 T here
    b.p(lam + np.pi / 2 + np.pi / 4, 0)            # p(lam) . s(0)
    b.tdg(0)
    b.p(lam - np.pi / 2 + np.pi / 4, 1)            # p(lam) . sdg(1)
    b.tdg(1)
    b.p(lam + np.pi / 2 + np.pi / 4, 2)
    b.tdg(2)
    b.sdg(2)
    b.p(lam + np.pi / 2 + np.pi / 4, 3)
    b.tdg(3)
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
            q4 = 1 if abs(float(wts[k])) == 0.25 else 0   # rz(+-beta/2): 64 + 1 T after a pi/4 shift instead of 66
            b.rz(2.0 * float(wts[k]) * beta * (-1) ** frame + sh * np.pi / 2 + q4 * np.pi / 4, 0)
            if q4:
                b.tdg(0)
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
