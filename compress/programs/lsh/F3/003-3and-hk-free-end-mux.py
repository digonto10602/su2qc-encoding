"""SUMMARY: native 3-AND frame of r01-F3-001 (raw l_nv parity folded into site 0, Margolus Toffolis on sites 1-3 only, f-collapse; 46 CX, 24 fixed T, no flag ancilla) with its 17-term ungated Walsh multiplexer re-toured exactly: Held-Karp over the support with BFS distances in the Cayley graph of all single-wire forms (p, e, u, v, y1-y3, w1-w3, outer l_2v/l_v1 of site 0) and free ends in span{e, v}; the walk starts free on e (merged into the collapse CX as CZ) and needs 24 toggles instead of 30, 70 CX, all angles k*beta/4 or 3*alpha/4.
DISCOVERY: (claim) the r01-F3-001 multiplexer support (17 terms, coefficients +-beta/4, +-beta/2) has an exact optimal open tour of 24 toggles once the outer pair (l_2v, l_v1) of site 0 is used as two generators (l_v1 = l_2v xor e) and the start is free on e; beam routing had 30, so the 3-AND frame gives 46 + 24 = 70 CX with no flag and 6 rccx-free Toffolis.
DISCOVERY: (claim) fresh time-limited MILP multiplexers in the same frame (19-21 terms) tour worse (31-33, same Held-Karp) than this 17-term support, and an add-and-prune local search finds no exact neighbouring support; y0 = (not e) AND l_2v(0) holds on all 433 states, but spending a 6-CX flag on it gives a 16-term support with a 27-toggle tour (79 CX).
"""
FAMILY = "F3"
PARENT = "r01-F3-001"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Walk on the pivot q0 (f0) in its H frame.  The start parity e is reached by a free toggle merged into the
# collapse CX(0, 9) as CZ.  WALK: (generator, c): CX(src, 0) then rz(c * beta) on q0 (c = 0: no rotation).
START_C = Fraction(-1, 2)
WALK = [("oB0", Fraction(-1, 4)), ("y1", Fraction(0)), ("w1", Fraction(-1, 4)), ("oB0", Fraction(-1, 4)),
        ("p", Fraction(0)), ("u", Fraction(-1, 4)), ("oA0", Fraction(-1, 4)), ("e", Fraction(0)),
        ("y1", Fraction(-1, 4)), ("y3", Fraction(0)), ("oB0", Fraction(-1, 4)), ("oA0", Fraction(-1, 4)),
        ("p", Fraction(0)), ("w3", Fraction(-1, 4)), ("oB0", Fraction(-1, 4)), ("u", Fraction(0)),
        ("y2", Fraction(0)), ("y3", Fraction(-1, 4)), ("oB0", Fraction(-1, 4)), ("p", Fraction(0)),
        ("w2", Fraction(-1, 4)), ("oA0", Fraction(-1, 4)), ("y2", Fraction(-1, 4)), ("p", Fraction(1, 4))]


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
    # single-wire forms after the frame: q1 = p (raw l_nv parity), q2 = w0 = e, q3 = u = f1^f3, q4 = y1,
    # q5 = w1 = e^u, q6 = v = f0^f2, q7 = y2, q8 = w2 = u^v^e, q9 = e = f0^f3, q10 = y3, q11 = w3 = v^e,
    # q13 = l_2v(0), q14 = l_v1(0) = l_2v(0)^e (outer, read only)
    src = {"p": 1, "e": 9, "u": 3, "y1": 4, "w1": 5, "v": 6, "y2": 7, "w2": 8, "y3": 10, "w3": 11,
           "oA0": 13, "oB0": 14}
    beta = spec.beta
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
    b.cx(9, 3)
    b.cx(0, 6)
    # collapse CX(0 -> 9) followed by CZ(0, 9): the CZ before h(0) is the free first toggle CX(9 -> 0) after it
    b.s(0)
    b.sdg(9)
    b.cx(0, 9)
    b.s(9)
    b.h(0)
    b.rz(float(START_C) * beta, 0)
    for g, c in WALK:
        b.cx(src[g], 0)
        if c != 0:
            b.rz(float(c) * beta, 0)
    b.h(0)
    b.cx(0, 9)
    b.cx(0, 6)
    b.cx(9, 3)
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
