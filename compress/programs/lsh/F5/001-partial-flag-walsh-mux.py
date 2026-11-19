"""SUMMARY: one partial flag F=[y0=y2=0] (1 rccx pair) + Walsh multiplexer over (u,v,e,F,y1,y3) with don't-cares, no full bright flag; walk = exact TSP over an 18-term MILP support (Gray-blocked walk model), first/last toggle merged into the ladder CX as CZ; 73 CX, 22 rotations k*beta/16, 25 qubits (does not beat the 71-CX seed).
DISCOVERY: with no bright flag the Walsh multiplexer over (u,v,e,y0..y3) needs all 16 y-characters (the f=0000/1111 link class sees every y pattern), an exact-16 solution is ILP-infeasible and a Gray-blocked walk costs >=31 toggles, so F5 without flags loses to the 71-CX seed.
DISCOVERY: a toggle CX(q,pivot) right after h(pivot) equals CZ(q,pivot) before it, so a first/last walk toggle on a qubit that the ladder CX(pivot,q) targets (v=q6, e=q9) is free (CX-then-CZ = sdg,s,cx,sdg); the seed uses this only at the end.
DISCOVERY: shifting the whole Walsh support by a dark-flag character (y_c) leaves the target unchanged (theta vanishes when y_c=1), so the walk may be re-toured on any shifted support; here it saved 1 CX (74 -> 73), on the seed support it does not help.
"""
FAMILY = "F5"
PARENT = None

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Frame: per-site transcoder cx(nv->vp), cx(nv->pn), rccx(vp, pn -> nv) leaves (f_c, y_c, w_c) in (pn, nv, vp) with
# y_c the dark flag of site c; ladder q3 = f1^f3 (u), q6 = f0^f2 (v), q9 = f0^f3 (e); the pivot q0 = f0 is the only
# bit the plaquette move flips.  The w slots hold link parities for free: q5 = u^e, q8 = u^v^e, q11 = v^e.
# One partial flag F = [y0 = y2 = 0] (ancilla); the gated rotation is a Walsh multiplexer over (u, v, e, F, y1, y3)
# with don't-cares on (link, flag) patterns no physical code reaches; no full bright flag is built.
# WALK entries: (toggle qubit, kind, coefficient c); rz(2*c*beta) on the pivot (H frame) after the toggle.
# kind "free": the first/last toggle is a CZ that merges into the ladder CX(0, q) / inverse ladder CX(0, q).
WALK = [
    (None, "start", Fraction(0, 1)),
    (9, "free", Fraction(0, 1)),
    (24, "cx", Fraction(3, 16)),
    (8, "cx", Fraction(3, 16)),
    (9, "cx", Fraction(3, 16)),
    (8, "cx", Fraction(-5, 16)),
    (10, "cx", Fraction(1, 4)),
    (24, "cx", Fraction(1, 4)),
    (4, "cx", Fraction(1, 8)),
    (10, "cx", Fraction(-1, 4)),
    (24, "cx", Fraction(1, 4)),
    (6, "cx", Fraction(0, 1)),
    (10, "cx", Fraction(3, 8)),
    (6, "cx", Fraction(-1, 2)),
    (3, "cx", Fraction(3, 8)),
    (6, "cx", Fraction(0, 1)),
    (24, "cx", Fraction(-3, 8)),
    (5, "cx", Fraction(0, 1)),
    (4, "cx", Fraction(-1, 2)),
    (10, "cx", Fraction(5, 16)),
    (8, "cx", Fraction(-3, 16)),
    (9, "cx", Fraction(-3, 16)),
    (8, "cx", Fraction(-3, 16)),
    (6, "free", Fraction(0, 1)),
]


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    (fl,) = b.alloc(1, "flag")
    assert fl == 24
    for c in range(4):
        b.cx(3 * c + 1, 3 * c + 2)
        b.cx(3 * c + 1, 3 * c)
        b.rccx(3 * c + 2, 3 * c, 3 * c + 1)
    for c in range(4):
        b.p(-0.75 * spec.alpha, 3 * c)
    b.x(1)
    b.x(7)
    b.rccx(1, 7, fl)               # F = [y0 = 0][y2 = 0]
    b.x(1)
    b.x(7)
    first = WALK[1][0] if WALK[1][1] == "free" else None
    last = WALK[-1][0] if WALK[-1][1] == "free" else None
    b.cx(9, 3)
    for t in (6, 9):
        if t != first:
            b.cx(0, t)
    if first is not None:          # cx(0, g) followed by cz(0, g)
        b.sdg(0)
        b.s(first)
        b.cx(0, first)
        b.sdg(first)
    b.h(0)
    for q, kind, c in WALK:
        if kind == "cx":
            b.cx(q, 0)
        if c != 0:
            b.rz(float(2 * c) * beta, 0)
    b.h(0)
    if last is not None:           # cz(0, g) followed by cx(0, g)
        b.s(0)
        b.s(last)
        b.cx(0, last)
        b.sdg(last)
    for t in (9, 6):
        if t != last:
            b.cx(0, t)
    b.cx(9, 3)
    b.x(1)
    b.x(7)
    b.rccx(1, 7, fl)
    b.x(1)
    b.x(7)
    b.free([fl])
    for c in reversed(range(4)):
        b.rccx(3 * c + 2, 3 * c, 3 * c + 1)
        b.cx(3 * c + 1, 3 * c)
        b.cx(3 * c + 1, 3 * c + 2)
    return b
