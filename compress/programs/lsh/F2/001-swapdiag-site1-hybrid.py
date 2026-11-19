"""SUMMARY: swap-diagonal frame on site 1 (cx, cx, ch: its nv/vp swap becomes a CZ, no AND) with real-phase Margolus recoding on sites 0, 2, 3; collapse to one moving qubit, flags a1=[y0=y2=0] and A=[u=v=0] in separate ancillas, and a 14-term angle-linear walk (MILP optimum over w0, A, y0, a1, nv1, y3, w1) whose target sign carries the CZ(w1, nv1) of the swap-diagonal site.
DISCOVERY: (claim, numerical) in the ch frame the only bright-zero garbage-free 1-AND flags are d_c = nv_c AND NOT w_c; no two of them cover the even-D dark collisions left by the raw nv parity p, so an all-ch (pure swap-diagonal) design needs >= 3 garbage-free ANDs for gating on top of p.
DISCOVERY: (claim, numerical) replacing one transcoded site by the ch frame saves 4 CX in the frame, but the walk support grows 12 -> 14 (TCTT, MILP optimum) and the shortest closed walk grows 13 -> 26 toggles; qiskit rccx recoding is then invalid (its (-i)^{rising} phase is no longer move-invariant), the h/t/cx Margolus is needed.
"""
FAMILY = "F2"
PARENT = None

from fractions import Fraction

from su2plaq.compress.builder import Builder

# atoms of the walk (bit -> name); qubits are fixed in build()
ATOMS = ["w0", "A", "z0", "a1", "z1", "z3", "w1"]
# closed walk over Walsh parities (bitmask over ATOMS) with rotation coefficient c (rz(2 c beta) on the target)
WALK = [(0, Fraction(0)), (68, Fraction(-1, 8)), (77, Fraction(1, 8)), (75, Fraction(-1, 8)), (66, Fraction(1, 8)),
        (112, Fraction(-1, 8)), (120, Fraction(1, 8)), (110, Fraction(-1, 8)), (102, Fraction(1, 8)),
        (38, Fraction(1, 8)), (54, Fraction(1, 8)), (62, Fraction(-1, 8)), (46, Fraction(-1, 8)),
        (26, Fraction(-1, 4)), (18, Fraction(1, 4)), (0, Fraction(0))]


def _ry(b, t, sign):
    # Ry(sign * pi/4) up to global phase: sdg h t h s
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


def build(spec):
    b = Builder(spec)
    T_SITES = (0, 2, 3)
    # ---- frame
    for c in T_SITES:
        pn, nv, vp = 3 * c, 3 * c + 1, 3 * c + 2
        b.cx(nv, vp)
        b.cx(nv, pn)
        _margolus(b, vp, pn, nv)          # nv -> dark flag y_c
    b.cx(4, 5)                            # site 1: vp -> w1
    b.cx(4, 3)                            # site 1: pn -> f1
    for q in (0, 3, 6, 9):                # U_E on the four link fluxes
        b.p(-0.75 * spec.alpha, q)
    b.cx(9, 3)                            # u = f1 ^ f3
    b.cx(0, 6)                            # v = f0 ^ f2
    b.cx(0, 9)                            # e = f3 ^ f0 = w0
    b.ch(5, 4)                            # swap-diagonal: CX(w1 -> nv1) becomes CZ(w1, nv1)
    a1, A = b.alloc(2, "flags")
    b.x(1); b.x(7)
    b.rccx(1, 7, a1)                      # a1 = [y0 = 0][y2 = 0]
    b.x(1); b.x(7)
    b.x(3); b.x(6)
    b.rccx(3, 6, A)                       # A = [u = 0][v = 0]
    b.x(3); b.x(6)
    qmap = {"w0": 9, "A": A, "z0": 1, "a1": a1, "z1": 4, "z3": 10, "w1": 5}
    b.h(0)
    cur = 0
    for S, coef in WALK:
        diff = cur ^ S
        for i, nm in enumerate(ATOMS):
            if (diff >> i) & 1:
                b.cx(qmap[nm], 0)
        cur = S
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
    b.ch(5, 4)
    b.cx(0, 9)
    b.cx(0, 6)
    b.cx(9, 3)
    b.cx(4, 3)
    b.cx(4, 5)
    for c in reversed(T_SITES):
        pn, nv, vp = 3 * c, 3 * c + 1, 3 * c + 2
        _margolus(b, vp, pn, nv, inverse=True)
        b.cx(nv, pn)
        b.cx(nv, vp)
    return b
