"""SUMMARY: headline r04-F3-004 fold frame (raw l_nv parity folded into site 0, Margolus Toffolis on sites 1-3; 46 CX, 24 fixed T) with the F5 all-pivot collapse (cx(0,3) instead of cx(9,3): q3 = w1 = f0^f1, so every collapse CX is pivot-controlled and free walk ends lie anywhere in span{u, v, e}) and the r04-F3-004 22-toggle walk (18 rotations, all k*beta/4); 68 CX, structural variant that ties the headline, no improvement.
DISCOVERY: (claim, derived on the frame variables and checked against the 433 physical states by the label table) on bright codes p = [u or v], so 2K = 2 if p = 1, else -4 (e = 0) or -1 (e = 1); with y0 = l_2v(0) and not e the step angle factorises as theta = [y1 = y2 = y3 = 0] * (1 - l_2v(0)*(1 - e)) * g(p, e), which explains why an exact support over (p, y1, y2, y3, e, l_2v(0)) alone exists.
DISCOVERY: (claim, numerical, SA not a bound) adding the outer pairs of sites 1-3 as walk generators raises the label count from 51 to 120 and SA (1.5 M steps, frames A and B) found no exact walk of <= 21 toggles; on the 51-label cube, 5 SA runs (2-3 M steps, frames A/B, with and without a support penalty) found exact walks of 23-26 toggles only, and a plateau walk from the 22-toggle headline walk found no neighbour with fewer toggles or fewer than 18 rotations.
"""
FAMILY = "F5"
PARENT = "r04-F3-004"

from fractions import Fraction

from su2plaq.compress.builder import Builder

FRAME = 'B'
START_MERGE = [9]
END_MERGE = []
START_C = Fraction(-1, 4)
WALK = [("oB0", Fraction(-1, 4)), ("y2", Fraction(0, 1)), ("p", Fraction(-1, 4)), ("oA0", Fraction(-1, 4)), ("y3", Fraction(-1, 4)), ("oB0", Fraction(-1, 4)), ("y2", Fraction(-1, 4)), ("y1", Fraction(0, 1)), ("y3", Fraction(-1, 4)), ("oB0", Fraction(-1, 4)), ("y2", Fraction(-1, 4)), ("oB0", Fraction(-1, 4)), ("y3", Fraction(1, 4)), ("p", Fraction(-1, 4)), ("oA0", Fraction(-1, 4)), ("p", Fraction(0, 1)), ("oB0", Fraction(-1, 4)), ("y2", Fraction(-1, 4)), ("oA0", Fraction(-1, 4)), ("y1", Fraction(-1, 4)), ("p", Fraction(0, 1)), ("y3", Fraction(0, 1))]
SRC = {'p': 1, 'e': 9, 'u': 3, 'y1': 4, 'w1': 5, 'v': 6, 'y2': 7, 'w2': 8, 'y3': 10, 'w3': 11, 'oA0': 13, 'oB0': 14}



def _ry8(b, q, sign):
    # Ry(sign*pi/4) up to global phase: S H T H Sdg (real matrix)
    b.sdg(q)
    b.h(q)
    if sign > 0:
        b.t(q)
    else:
        b.tdg(q)
    b.h(q)
    b.s(q)


def margolus(b, a, c, t):
    """Real-phase Toffoli (Margolus): CCX(a, c -> t) times -1 on |a=1, c=0, t=1>; self-inverse; 3 CX, 4 T."""
    _ry8(b, t, +1)
    b.cx(c, t)
    _ry8(b, t, +1)
    b.cx(a, t)
    _ry8(b, t, -1)
    b.cx(c, t)
    _ry8(b, t, -1)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    # frame: q1 = raw l_nv parity p, q2 = w0, sites 1-3 (cx, cx, Margolus) -> f_c, y_c, w_c
    b.cx(1, 2)
    b.cx(1, 0)
    b.cx(4, 1)
    b.cx(7, 1)
    b.cx(10, 1)
    for c in (1, 2, 3):
        b.cx(3 * c + 1, 3 * c + 2)
        b.cx(3 * c + 1, 3 * c)
        margolus(b, 3 * c, 3 * c + 2, 3 * c + 1)
    for q in (0, 3, 6, 9):
        b.p(-0.75 * spec.alpha, q)
    src = dict(SRC)
    if FRAME == "A":
        coll = [(9, 3), (0, 6), (0, 9)]
    else:
        # all-pivot collapse: q3 = f0 ^ f1 = w1, so u is not a single wire
        coll = [(0, 3), (0, 6), (0, 9)]
        src["w1"] = 3
        src.pop("u")
    # collapse; a free start toggle on collapse target t is a CZ(0, t) merged into CX(0, t)
    for (c, t) in coll:
        if c == 0 and t in START_MERGE:
            b.s(0)
            b.sdg(t)
            b.cx(0, t)
            b.s(t)
        else:
            b.cx(c, t)
    b.h(0)
    if START_C != 0:
        b.rz(float(START_C) * beta, 0)
    for gname, cf in WALK:
        b.cx(src[gname], 0)
        if cf != 0:
            b.rz(float(cf) * beta, 0)
    b.h(0)
    for (c, t) in reversed(coll):
        if c == 0 and t in END_MERGE:
            b.sdg(t)
            b.cx(0, t)
            b.s(t)
            b.sdg(0)
        else:
            b.cx(c, t)
    for c in (3, 2, 1):
        margolus(b, 3 * c, 3 * c + 2, 3 * c + 1)
        b.cx(3 * c + 1, 3 * c)
        b.cx(3 * c + 1, 3 * c + 2)
    b.cx(10, 1)
    b.cx(7, 1)
    b.cx(4, 1)
    b.cx(1, 0)
    b.cx(1, 2)
    return b
