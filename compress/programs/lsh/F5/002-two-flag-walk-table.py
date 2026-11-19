"""SUMMARY: F5 restart from the seed core: per-site transcoder, ladder (u, v, e), flags a1=[y0=y2=0] (ancilla) and A=[u=v=0] XORed into y0, 13+1-toggle pivot walk with the last e-toggle merged into the inverse ladder; table-driven walk with free first/last CZ merges; 71 CX, 17 rotations k*beta/8 or 3*alpha/4 (ties the seed, does not beat it).
DISCOVERY: (claim, numerical, simulated annealing over closed toggle walks with generators u,v,e,u^e,v^e,u^v^e,y0..y3 and two AND flags) with a1=[y_i=y_j=0] for any corner pair and A=[u=v=0] (ancilla or in place in any y slot) no closed walk of cost 12 (14 toggles with both ends free on e/v, or 13 with one) was found; all cost-13 walks found use the pair (0,2) and 13-14 rotations, so the seed walk is a robust local optimum.
DISCOVERY: (claim, numerical) the three w slots give the free link forms u^e, v^e, u^v^e on all 47 codes (w_c = f_c xor f_{c-1}, also on dark codes; w_0 = e duplicates the ladder qubit), but adding them as walk generators did not shorten the two-flag walk below 13 nor let SA reach a one-flag walk of <= 18 toggles (SA also fails to re-find the parent's 21-toggle walk, so this is not a lower bound).
DISCOVERY: (claim) the minimum Walsh support with the seed flags is 12 (HiGHS MILP, 114 s) while the seed walk needs 13 rotations (exhaustive subset check on its 14 visited parities), so a 12-rotation walk would save about 60 T at 71 CX if a 13-toggle tour through such a support exists.
"""
FAMILY = "F5"
PARENT = "r01-F5-001"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Frame after the per-site transcoder cx(nv->vp), cx(nv->pn), rccx(vp, pn -> nv): (pn, nv, vp) = (f_c, y_c, w_c),
# y_c the dark flag of site c.  Ladder: q3 = f1^f3 (u), q6 = f0^f2 (v), q9 = f0^f3 (e); the pivot q0 = f0 is the only
# bit the plaquette move flips.  Flags: a1 = [y0 = y2 = 0] in an ancilla, then A = [u = v = 0] XORed into q1 (y0).
# WALK entries: (toggle qubit, kind, coefficient c); rz(2*c*beta) on the pivot (H frame) after the toggle.
# kind "free": a first/last toggle on a ladder target (q6 or q9), merged with the ladder CX as a CZ.
FLAG = "a1"
WALK = [
    (None, "start", Fraction(1, 2)),
    (4, "cx", Fraction(-1, 4)),
    (FLAG, "cx", Fraction(1, 4)),
    (10, "cx", Fraction(-1, 8)),
    (1, "cx", Fraction(-3, 8)),
    (FLAG, "cx", Fraction(3, 8)),
    (1, "cx", Fraction(1, 8)),
    (4, "cx", Fraction(-1, 4)),
    (FLAG, "cx", Fraction(1, 4)),
    (10, "cx", Fraction(-1, 8)),
    (1, "cx", Fraction(-3, 8)),
    (FLAG, "cx", Fraction(0, 1)),
    (9, "cx", Fraction(3, 8)),
    (1, "cx", Fraction(-3, 8)),
    (9, "free", Fraction(0, 1)),
]


def _flags(b, fl):
    b.x(1)
    b.x(7)
    b.rccx(1, 7, fl)               # a1 = [y0 = 0][y2 = 0]
    b.x(1)
    b.x(3)
    b.x(6)
    b.rccx(3, 6, 1)                # q1 = y0 ^ A, A = [u = 0][v = 0]; q7 stays negated (unused by the walk)


def _unflags(b, fl):
    b.rccx(3, 6, 1)
    b.x(3)
    b.x(6)
    b.x(1)
    b.rccx(1, 7, fl)
    b.x(1)
    b.x(7)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    (fl,) = b.alloc(1, "flag")
    for c in range(4):
        b.cx(3 * c + 1, 3 * c + 2)
        b.cx(3 * c + 1, 3 * c)
        b.rccx(3 * c + 2, 3 * c, 3 * c + 1)
    for c in range(4):
        b.p(-0.75 * spec.alpha, 3 * c)
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
    _flags(b, fl)
    b.h(0)
    for q, kind, c in WALK:
        if kind == "cx":
            b.cx(fl if q == FLAG else q, 0)
        if c != 0:
            b.rz(float(2 * c) * beta, 0)
    b.h(0)
    _unflags(b, fl)
    if last is not None:           # cz(0, g) followed by cx(0, g)
        b.sdg(0)
        b.sdg(last)
        b.cx(0, last)
        b.s(last)
    for t in (9, 6):
        if t != last:
            b.cx(0, t)
    b.cx(9, 3)
    b.free([fl])
    for c in reversed(range(4)):
        b.rccx(3 * c + 2, 3 * c, 3 * c + 1)
        b.cx(3 * c + 1, 3 * c)
        b.cx(3 * c + 1, 3 * c + 2)
    return b
