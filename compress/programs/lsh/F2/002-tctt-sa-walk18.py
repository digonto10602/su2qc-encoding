"""SUMMARY: parent's TCTT layout (site 1 swap-diagonal cx, cx, ch; Margolus transcoder on sites 0, 2, 3; flags a1=[y0=y2=0], A=[u=v=0]) with the walk re-optimised for toggle count: simulated annealing directly over toggle sequences (atoms e, v, u, w1=u^e, w3=v^e, A, a1, nv1, y3; link forms from the w slots) gives an 18-toggle closed walk with 15 rotations (MILP min on the visited sets, all k*beta/8), 72 CX instead of 80.
DISCOVERY: (claim, numerical) in the TCTT swap-diagonal layout the shortest closed walk found by SA over toggle sequences is 18 toggles (none at 15, 16 or 17 in about 30, 10 and 35 SA runs, start/end merges with the ladder CX on v, e allowed), so TCTT costs 42 + 12 + 18 = 72 CX, one above the 71-CX seed; the parent's 26-toggle tour came from a min-support MILP that ignores tour length.
DISCOVERY: (claim, numerical) the w-slot link forms w1=u^e and w3=v^e are free single-qubit toggles; w1 appears in all four 18-toggle TCTT walks found; Held-Karp re-touring of the 15-term support with dark-flag shifts (y3, a1) does not shorten it below 18.
"""
FAMILY = "F2"
PARENT = "r01-F2-001"

from fractions import Fraction

from su2plaq.compress.builder import Builder

TYPES = 'TCTT'          # per site: "T" = Margolus transcoder, "C" = swap-diagonal (cx, cx, ch)
S0 = ()                # walk start atoms, merged into the forward ladder CX(pivot -> q) as CZ
WALK = [(None, Fraction(-1, 8)), ('w1', Fraction(1, 8)), ('z1', Fraction(-1, 8)), ('a1', Fraction(1, 8)), ('A', Fraction(0, 1)), ('z1', Fraction(-1, 8)), ('w1', Fraction(-1, 8)), ('z1', Fraction(-1, 8)), ('a1', Fraction(1, 8)), ('z3', Fraction(1, 4)), ('a1', Fraction(-1, 4)), ('w3', Fraction(0, 1)), ('z1', Fraction(-1, 8)), ('A', Fraction(1, 8)), ('a1', Fraction(-1, 8)), ('A', Fraction(1, 8)), ('w3', Fraction(0, 1)), ('z3', Fraction(1, 4)), ('A', Fraction(0, 1))]            # (toggle atom or None, coefficient c): CX(atom -> pivot), then rz(2 c beta)
END = ()              # walk end atoms, merged into the inverse ladder CX(pivot -> q) as CZ


def _ry(b, t, sign):
    b.sdg(t)
    b.h(t)
    if sign > 0:
        b.t(t)
    else:
        b.tdg(t)
    b.h(t)
    b.s(t)


def _margolus(b, a, c, t, inverse=False):
    """Real-phase Toffoli (3 CX): exact Toffoli except -1 on |a=1, c=0, t=1>."""
    seq = [("ry", 1), ("cx", c), ("ry", 1), ("cx", a), ("ry", -1), ("cx", c), ("ry", -1)]
    if inverse:
        seq = [(g, -v) if g == "ry" else (g, v) for g, v in reversed(seq)]
    for g, v in seq:
        if g == "ry":
            _ry(b, t, v)
        else:
            b.cx(v, t)


def _ladder_cx(b, q, merge, start):
    # CX(0 -> q) fused with CZ(q, 0) (after it if start, before it if end): one CX
    if not merge:
        b.cx(0, q)
        return
    b.sdg(q)
    b.cx(0, q)
    b.s(q)
    if start:
        b.s(0)
    else:
        b.sdg(0)


def build(spec):
    b = Builder(spec)
    for c in range(4):
        pn, nv, vp = 3 * c, 3 * c + 1, 3 * c + 2
        b.cx(nv, vp)                      # vp -> w_c
        b.cx(nv, pn)                      # pn -> f_c
        if TYPES[c] == "T":
            _margolus(b, vp, pn, nv)      # nv -> dark flag y_c
    for q in (0, 3, 6, 9):                # U_E on the four link fluxes
        b.p(-0.75 * spec.alpha, q)
    b.cx(9, 3)                            # u = f1 ^ f3
    _ladder_cx(b, 6, "v" in S0, True)     # v = f0 ^ f2
    _ladder_cx(b, 9, "e" in S0, True)     # e = f0 ^ f3
    for c in range(4):
        if TYPES[c] == "C":
            b.ch(3 * c + 2, 3 * c + 1)    # swap-diagonal: move on nv_c becomes Z
    a1, A = b.alloc(2, "flags")
    b.x(1); b.x(7)
    b.rccx(1, 7, a1)                      # a1 = [y0 = 0][y2 = 0]
    b.x(1); b.x(7)
    b.x(3); b.x(6)
    b.rccx(3, 6, A)                       # A = [u = 0][v = 0]
    b.x(3); b.x(6)
    qmap = {"e": 9, "v": 6, "u": 3, "w0": 2, "w1": 5, "w2": 8, "w3": 11, "A": A, "a1": a1,
            "z0": 1, "z1": 4, "z2": 7, "z3": 10}
    b.h(0)
    for g, coef in WALK:
        if g is not None:
            b.cx(qmap[g], 0)
        if coef != 0:
            b.rz(float(2 * coef) * spec.beta, 0)
    b.h(0)
    b.x(3); b.x(6)
    b.rccx(3, 6, A)
    b.x(3); b.x(6)
    b.x(1); b.x(7)
    b.rccx(1, 7, a1)
    b.x(1); b.x(7)
    b.free([a1, A])
    for c in range(4):
        if TYPES[c] == "C":
            b.ch(3 * c + 2, 3 * c + 1)
    _ladder_cx(b, 9, "e" in END, False)
    _ladder_cx(b, 6, "v" in END, False)
    b.cx(9, 3)
    for c in reversed(range(4)):
        pn, nv, vp = 3 * c, 3 * c + 1, 3 * c + 2
        if TYPES[c] == "T":
            _margolus(b, vp, pn, nv, inverse=True)
        b.cx(nv, pn)
        b.cx(nv, vp)
    return b
