"""SUMMARY: F1-002 frame (per-site cx, cx, rccx; raw l_nv parity folded into vp_0 = w0^p; flag a=[y0=y2=0]) with an all-pivot-controlled ladder (free walk ends in span{u, v, e}) and the F1-002 13-term support re-toured by an Eulerian-trail MILP (edge multiplicities + single-commodity flow, free ends via a super node): 15 paid toggles from the free start e, 71 CX, 10 rccx, 17 rotations, all angles k*beta/4 or 3*alpha/4; no walk of <= 14 toggles was found, so this is a structural variant, not an improvement.
DISCOVERY: (claim, numerical, not a proof) re-touring the F1-002 13-term support in the 7-variable cube (e, v, u, pe, a, y1, y3) with all single-wire forms e, v, v^e, u^e, u^v^e as generators, free ends anywhere in span{u, v, e} and the 8 dark-flag shifts span{a, y1, y3} gives no tour below 15 (exact Held-Karp); the 7-cube minimum Walsh support is 12 (HiGHS, optimal), but random L1-LP supports of size 12-15 tour at >= 20.
DISCOVERY: (claim, numerical, time-limited HiGHS, no incumbent = not a proof) no walk of <= 14 paid toggles was found for the F1 frame in the cubes (e, v, u, pe, a, y1, y3) (900 s Eulerian MILP + 12 min time-indexed MILP), (e, v, pe, a, y1, y3) and (e, u, pe, a, y1, y3) (420 s each), nor a walk of <= 18 toggles for the plain 52-CX frame (e, v, u, a, y1, y3) (time-indexed MILP stopped after 4 min); the same Eulerian MILP also found no incumbent at <= 15 toggles in the 7-cube in 700 s although the F1-002 walk exists there, so these searches are weak; the sparsest Walsh support found for the plain frame has 18 terms (HiGHS, 150 s, not proven minimal).
"""
FAMILY = "F1"
PARENT = "r02-F1-002"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Frame of F1-002 (per-site cx, cx, rccx; raw l_nv parity folded into vp_0 = w0^p; flag a = [y0 = y2 = 0]) with an
# all-pivot-controlled ladder cx(0,3), cx(0,6), cx(0,9) (q3 = f0^f1 = u^e, q6 = v, q9 = e).  Walk on the pivot q0 in
# its H frame.  START / END: free toggles on the ladder targets (merged into the ladder CX as CZ).  WALK: (toggle, c)
# pairs, toggle CX(src, 0) then rz(c*beta).  Forms: e = q9, pe = q2 (w0^p), v = q6, ue = q3/q5, uve = q8, ve = q11.
START = ['e']
START_C = Fraction(-3, 4)
WALK = [("pe", Fraction(-3, 4)), ("a", Fraction(3, 4)), ("y3", Fraction(0, 1)), ("y1", Fraction(0, 1)), ("a", Fraction(-3, 4)), ("a", Fraction(0, 1)), ("e", Fraction(3, 4)), ("pe", Fraction(-1, 4)), ("y3", Fraction(1, 2)), ("a", Fraction(-1, 2)), ("y3", Fraction(1, 4)), ("y1", Fraction(-1, 2)), ("a", Fraction(1, 2)), ("y3", Fraction(-1, 4)), ("a", Fraction(1, 1))]
END = []


def build(spec):
    b = Builder(spec)
    (a,) = b.alloc(1, "flag")
    src = {"a": a, "pe": 2, "e": 9, "v": 6, "ue": 3, "ue2": 5, "uve": 8, "ve": 11, "y0": 1, "y1": 4, "y2": 7, "y3": 10}
    lad = {"ue": 3, "v": 6, "e": 9}
    beta = spec.beta

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
    for g in ("ue", "v", "e"):
        if g in START:
            cx_cz(lad[g])
        else:
            b.cx(0, lad[g])
    flag()
    b.h(0)
    if START_C != 0:
        b.rz(float(START_C) * beta, 0)
    for g, c in WALK:
        b.cx(src[g], 0)
        if c != 0:
            b.rz(float(c) * beta, 0)
    b.h(0)
    for g in ("e", "v", "ue"):
        if g in END:
            cz_cx(lad[g])
        else:
            b.cx(0, lad[g])
    flag()
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
