"""SUMMARY: LSH recoder (cx, cx, rccx per site) with the class bit taken from the raw l_nv parity: vp_0 <- vp_0^nv_1^nv_2^nv_3 = w_0^p (+2 CX per side) and site 0's Toffoli on (not f_3, f_0), which replaces the A=[u=v=0] rccx pair of the spin-network core; one flag a=[y0=y2=0]; 17-toggle walk on (w0, w0^p, a, y1, y3) ending on w0 (merged into the inverse collapse); 73 CX, 16 rotations, all angles k*beta/4 or 3*alpha/4.
DISCOVERY: (claim) on all 47 codes A=[u=v=0] equals not-p on bright codes, so the raw l_nv parity folded into the vp_0 slot (vp_0^nv_1^nv_2^nv_3 = w_0^p, Toffoli of site 0 on (not f_3, f_0) by the Gauss law) replaces the A rccx pair (4 CX instead of 6); the frame is valid with any correct walk.
DISCOVERY: (claim) the A->p swap does not pay: with walk variables (w0, w0^p, a=[y_i=y_j=0], two other y) the minimum Walsh support is 12 (MILP) but an exhaustive C DFS finds no toggle walk of <= 13 CX for any of the six corner-pair flags and none of <= 14 CX for a=[y0=y2=0]; best found 17 (MILP support + TSP), i.e. 73 CX vs 71.
DISCOVERY: (claim) the rccx relative phases of the per-site recoder cancel around the walk because the number of rising flux boundaries (f_{c-1}=0, f_c=1) is invariant under the move (it equals half the number of set w bits)."""
FAMILY = "F1"
PARENT = None

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Walk on the pivot q0 (f0) in its H frame: each step toggles one control onto the pivot (CX), then rz(c*beta).
# Controls: 'e' = q9 (w0 after the collapse), 'pe' = q2 (vp0 slot = w0 ^ p, p = parity of the four raw l_nv bits),
# 'a' = ancilla flag a = [y0=y2=0], 'y0'..'y3' = l_nv slots after the recoding (dark-site flags).
WALK = [("start", Fraction(0, 1)), ("y1", Fraction(-1, 4)), ("pe", Fraction(-1, 4)), ("a", Fraction(1, 4)), ("e", Fraction(0, 1)), ("pe", Fraction(1, 4)), ("pe", Fraction(0, 1)), ("y3", Fraction(1, 2)), ("a", Fraction(-1, 2)), ("e", Fraction(0, 1)), ("y1", Fraction(-1, 4)), ("e", Fraction(0, 1)), ("pe", Fraction(-1, 4)), ("a", Fraction(1, 4)), ("pe", Fraction(1, 4)), ("y3", Fraction(1, 2)), ("a", Fraction(-1, 2)), ("pe", Fraction(0, 1))]
END_E = True


def build(spec):
    b = Builder(spec)
    (a,) = b.alloc(1, "flag")
    src = {"a": a, "pe": 2, "e": 9, "v": 6, "y0": 1, "y1": 4, "y2": 7, "y3": 10}

    def recode_raw_parity():
        for c in (1, 2, 3):
            b.cx(3 * c + 1, 3 * c + 2)    # vp_c -> w_c = l_nv ^ l_vp
            b.cx(3 * c + 1, 3 * c)        # pn_c -> f_c = l_pn ^ l_nv (flux of the next inner link)
        b.cx(4, 2)
        b.cx(7, 2)
        b.cx(10, 2)                       # vp_0 -> vp_0 ^ nv_1 ^ nv_2 ^ nv_3 = w_0 ^ p (move-invariant)
        b.cx(1, 0)                        # pn_0 -> f_0

    def ands():
        for c in (1, 2, 3):
            b.rccx(3 * c + 2, 3 * c, 3 * c + 1)   # nv_c -> y_c = nv_c ^ w_c f_c
        b.x(9)
        b.rccx(9, 0, 1)                   # nv_0 -> y_0 = nv_0 ^ (not f_3) f_0  (= w_0 f_0 by Gauss)
        b.x(9)

    def flag():
        b.x(1); b.x(7)
        b.rccx(1, 7, a)
        b.x(1); b.x(7)

    recode_raw_parity()
    ands()
    for q in (0, 3, 6, 9):
        b.p(-0.75 * spec.alpha, q)
    b.cx(9, 3)
    b.cx(0, 6)
    b.cx(0, 9)                            # q9 = f3 ^ f0 = w0
    flag()
    b.h(0)
    for g, c in WALK:
        if g != "start":
            b.cx(src[g], 0)
        if c != 0:
            b.rz(float(c) * spec.beta, 0)
    if END_E:
        b.h(0)
        b.sdg(0)
        b.sdg(9)
        b.cx(0, 9)
        b.s(9)
    else:
        b.h(0)
        b.cx(0, 9)
    flag()
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
