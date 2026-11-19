"""SUMMARY: parent frame (per-site cx, cx, rccx; class bit = raw l_nv parity folded into vp_0 = w0^p; flag a=[y0=y2=0]) with a 15-toggle walk: first toggle on e=q9 merged into the collapse CX as CZ (free), walk variables (e, pe, a, y1, y3) over a 13-term support (MILP support enumeration + Hamiltonian-path DP with free ends in span{e, v}); 71 CX, 10 rccx (T_fixed 40), 17 rotations, all angles k*beta/4 or 3*alpha/4.
DISCOVERY: (claim) every walk toggle CX(q, pivot) before the first or after the last rotation, with q a target of a pivot-controlled collapse CX (here e=q9, v=q6), is free (CZ merged into that CX), so the walk is a path with free ends anywhere in span{e, v}; this turns the parent's 17-toggle walk into 15 and ties the seed at 71 CX with 8 fewer fixed T.
DISCOVERY: (claim, exhaustive C DFS) in the seed frame no walk of <= 12 toggles exists even with free ends in span{v, e} and v as an extra walk variable (variables q1=y0^A, y1, y3, a, e, v); the six 13-toggle seed walks (start 0, end 0 or e, no v) all need 13 rotations."""
FAMILY = "F1"
PARENT = "r01-F1-001"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Walk on the pivot q0 (f0) in its H frame.  START / END: free toggles on the ladder targets e=q9, v=q6
# (merged into the ladder CX as CZ).  WALK: (toggle, c) pairs, toggle CX(src, 0) then rz(c*SIGN*beta).
# 'e' = q9 (w0), 'v' = q6 (f0^f2), 'pe' = q2 (w0^p), 'a' = flag [y0=y2=0], 'y0'..'y3' = dark-site flags.
START = ['e']
START_C = Fraction('-3/4')
WALK = [("pe", Fraction(-3, 4)), ("a", Fraction(3, 4)), ("a", Fraction(0, 1)), ("y1", Fraction(0, 1)), ("y3", Fraction(-3, 4)), ("e", Fraction(0, 1)), ("a", Fraction(3, 4)), ("pe", Fraction(-1, 4)), ("y3", Fraction(1, 2)), ("y1", Fraction(-1, 4)), ("y3", Fraction(1, 2)), ("a", Fraction(-1, 2)), ("y1", Fraction(1, 4)), ("y3", Fraction(-1, 2)), ("y1", Fraction(1, 1))]
END = []
SIGN = 1


def build(spec):
    b = Builder(spec)
    (a,) = b.alloc(1, "flag")
    src = {"a": a, "pe": 2, "e": 9, "v": 6, "y0": 1, "y1": 4, "y2": 7, "y3": 10}
    beta = SIGN * spec.beta

    def cx_cz(q):      # time order CX(0->q) then CZ(0,q)
        b.s(0); b.sdg(q); b.cx(0, q); b.s(q)

    def cz_cx(q):      # time order CZ(0,q) then CX(0->q)
        b.sdg(0); b.sdg(q); b.cx(0, q); b.s(q)

    def flag():
        b.x(1); b.x(7)
        b.rccx(1, 7, a)
        b.x(1); b.x(7)

    for c in (1, 2, 3):
        b.cx(3 * c + 1, 3 * c + 2)        # vp_c -> w_c
        b.cx(3 * c + 1, 3 * c)            # pn_c -> f_c
    b.cx(4, 2)
    b.cx(7, 2)
    b.cx(10, 2)                           # vp_0 -> w_0 ^ p
    b.cx(1, 0)                            # pn_0 -> f_0
    for c in (1, 2, 3):
        b.rccx(3 * c + 2, 3 * c, 3 * c + 1)   # nv_c -> y_c
    b.x(9)
    b.rccx(9, 0, 1)                       # nv_0 -> y_0 (controls not f_3, f_0)
    b.x(9)
    for q in (0, 3, 6, 9):
        b.p(-0.75 * spec.alpha, q)
    b.cx(9, 3)
    if "v" in START:
        cx_cz(6)
    else:
        b.cx(0, 6)
    if "e" in START:
        cx_cz(9)
    else:
        b.cx(0, 9)
    flag()
    b.h(0)
    if START_C != 0:
        b.rz(float(START_C) * beta, 0)
    for g, c in WALK:
        b.cx(src[g], 0)
        if c != 0:
            b.rz(float(c) * beta, 0)
    b.h(0)
    if "e" in END:
        cz_cx(9)
    else:
        b.cx(0, 9)
    flag()
    if "v" in END:
        cz_cx(6)
    else:
        b.cx(0, 6)
    b.cx(9, 3)
    b.x(9)
    b.rccx(9, 0, 1)
    b.x(9)
    for c in (3, 2, 1):
        b.rccx(3 * c + 2, 3 * c, 3 * c + 1)
    b.cx(1, 0)
    b.cx(10, 2)
    b.cx(7, 2)
    b.cx(4, 2)
    for c in (3, 2, 1):
        b.cx(3 * c + 1, 3 * c)
        b.cx(3 * c + 1, 3 * c + 2)
    b.free([a])
    return b
