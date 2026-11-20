"""SUMMARY: time-reversed parent walk (r03-F5-003 frame: F1-002 fold frame, all-pivot ladder, flag a=[y0=y2=0]): the 15-toggle walk runs backwards from character 0 and its last toggle on e=q9 is merged as CZ into the inverse ladder CX instead of the first one into the forward ladder; 71 CX, 17 rotations, structural variant (exact 6-variable walk searches for <= 18 toggles on the 52-CX plain frame did not finish in budget; no 70-CX walk found).
DISCOVERY: (claim, HiGHS min-support MILP 60 s per solve + exact Held-Karp) on the plain 52-CX frame with walk coordinates (e, v, u, a, y1, y3), generators e, v, u^e, u^v^e, v^e, a, y1, y3 and free ends in span{u, v, e}, the smallest Walsh support found has 17 terms and both 17-term supports found need 22 paid toggles (74 CX), so a <= 18-toggle walk there must use a non-minimum support.
DISCOVERY: (claim) in that cube the bright layer (a, y1, y3) = (1, 0, 0) fixes all 8 Walsh coefficients over (u, v, e) to nonzero values (7/8; -9/8 on u, v, u^v; -3/8 on the four characters containing e), so every walk must visit all 8 S-columns; the 22 dark points add only vanishing conditions (30 points, null dimension 34).
"""
FAMILY = "F5"
PARENT = "r03-F5-003"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Walk on the pivot q0 (f0) in its H frame.  START / END: free toggles on the ladder targets e=q9, v=q6
# (merged into the ladder CX as CZ).  WALK: (toggle, c) pairs, toggle CX(src, 0) then rz(c*SIGN*beta).
# 'e' = q9 (w0), 'v' = q6 (f0^f2), 'pe' = q2 (w0^p), 'a' = flag [y0=y2=0], 'y0'..'y3' = dark-site flags.
START = []
START_C = Fraction('1')
WALK = [("y1", Fraction(-1, 2)), ("y3", Fraction(1, 4)), ("y1", Fraction(-1, 2)), ("a", Fraction(1, 2)), ("y3", Fraction(-1, 4)), ("y1", Fraction(1, 2)), ("y3", Fraction(-1, 4)), ("pe", Fraction(3, 4)), ("a", Fraction(0, 1)), ("e", Fraction(-3, 4)), ("y3", Fraction(0, 1)), ("y1", Fraction(0, 1)), ("a", Fraction(3, 4)), ("a", Fraction(-3, 4)), ("pe", Fraction(-3, 4))]
END = ['e']
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
    b.cx(0, 3)
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
    b.cx(0, 3)
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
