"""SUMMARY: F1 link-flag GHZ frame (flip qubit F = g_b): link prep with g copies in R2, U_E as 4 phases on L2, per-corner CX+CCX (CZ.CX merged, CS^dag + rccx), r folded into the R2 slots, sector height h_b by a flip-invariant 3-way rccx mux whose selectors also give K1=[r=101] and z=[r=000], tau removed by plain CX(h_X->e1) before a relative-phase 2-control H, closed-pair GHZ gadget; bright flag = NOR of 4 rccx-folded e1 plus z & e2=1111 for the closed pair; one 8-term Gray-cycle uniformly controlled Rz on F (8 CX); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: after the g-controlled corner Toffolis the equal-corner partner mismatch tau_c equals the sector height h_X; XOR-ing h_X into e1 BEFORE the controlled H (a sign on the singlet, a flip on the 00 member) removes it with CX only, no Toffoli; h_b itself is a 3-way mux of the [N_c=3] bits of different corners selected by r.
DISCOVERY: in this frame every bright label has e1=0000 and bright <=> e1=0000 and e2_c=1 at every equal corner (T+- have e2=0); 4 rccx folds (T+- at c0,c1,c2,c3 -> flip e1 of c0,c3,c0,c1) reduce the 80 non-closed pairs to a NOR of the 4 e1, but in r=000 all 256 (e1,e2) patterns are occupied, so the closed pair needs the full 8-bit check.
DISCOVERY: the GHZ-frame coupling sign is (-1)^(r_r+r_t+r_l); the relative-phase CCH (CCZ.CS^dag, 4 CX) adds (-i)^(g_X g_Y) = -1 exactly for pairs with adjacent equal corners, which cancels that sign for all 81 pairs, so no CZ is needed.
"""
FAMILY = "F1"
PARENT = None

import math

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
_CORN = [(0, 12, 1, 13), (2, 4, 1, 5), (6, 10, 5, 9), (8, 14, 9, 13)]   # (e1, e2, g_X, g_Y) per corner


def _inv(ops):
    out = []
    for name, p, qs in reversed(ops):
        if name in _INV:
            out.append((_INV[name], p, qs))
        elif name in ("rz", "p", "crx", "crz", "cp"):
            out.append((name, (-p[0],), qs))
        else:
            out.append((name, p, qs))
    return out


class _G:
    def __init__(self):
        self.o = []

    def g(self, n, *qs, p=()):
        self.o.append((n, tuple(p), tuple(qs)))

    def x(self, q):
        self.g("x", q)

    def cx(self, a, b):
        self.g("cx", a, b)

    def ccx(self, a, b, t):
        self.g("ccx", a, b, t)

    def rccx(self, a, b, t, na=False, nb=False):
        if na:
            self.x(a)
        if nb:
            self.x(b)
        self.g("rccx", a, b, t)
        if nb:
            self.x(b)
        if na:
            self.x(a)

    def cch(self, a, b, t, na=False, nb=False):
        """controlled-controlled-H = Ry(pi/4) CCZ Ry(-pi/4) on t, Ry(+-pi/4) = S H T^(+-1) H S^dag (phases cancel)."""
        if na:
            self.x(a)
        if nb:
            self.x(b)
        for n in ("sdg", "h", "tdg", "h"):
            self.g(n, t)
        self.g("ccz", a, b, t)
        for n in ("h", "t", "h", "s"):
            self.g(n, t)
        if nb:
            self.x(b)
        if na:
            self.x(a)


def _cch_rel(G, a, b, t):
    """controlled-controlled-H up to the control phase (-i)^(a b): Ry(pi/4) [CCZ . CS^dag(a, b)] Ry(-pi/4) on t (4 CX)."""
    for n in ("sdg", "h", "tdg", "h"):
        G.g(n, t)
    G.g("t", t)
    G.cx(a, t)
    G.g("tdg", t)
    G.cx(b, t)
    G.g("t", t)
    G.cx(a, t)
    G.g("tdg", t)
    G.cx(b, t)
    for n in ("h", "t", "h", "s"):
        G.g(n, t)


def _ops(alpha, beta, anc):
    A1, A2, K1, T23, T1, X1, Y1, Y2, Y3, Y4 = anc
    RR, RT, RL = 7, 11, 15                    # r bits live in the R2 slots of links r, t, l
    prep = _G()
    for l in range(4):
        prep.cx(4 * l, 4 * l + 1)             # L2 = g_l (Q flag)
        prep.cx(4 * l + 2, 4 * l + 3)         # R2 = g_l (copy) on valid codes
    ue = _G()
    for l in range(4):
        ue.g("p", 4 * l + 1, p=(-0.75 * alpha,))   # U_E = exp(-i 3/4 alpha #Q)
    D = _G()
    for e1, e2, gX, gY in _CORN:
        # CX(e1->e2) then CCX(g_X, e2 -> e1), as [CZ.CX merged] + CS^dag(e2, g_X) + rccx (6 CX instead of 7)
        D.g("sdg", e2)
        D.cx(e1, e2)
        D.g("s", e2)
        D.g("s", e1)
        D.g("tdg", e2)
        D.g("tdg", gX)
        D.cx(gX, e2)
        D.g("t", e2)
        D.cx(gX, e2)
        D.g("rccx", e2, gX, e1)               # e1 = [N_c = 3] at different corners
    for q in (3, RR, RT, RL):
        D.cx(1, q)                            # q3 = 0, r = (r_r, r_t, r_l) = g_x ^ g_b; F = q1 = g_b
    # class selectors and the sector height h_b into q3 (all inputs flip-invariant on bright states)
    D.rccx(RL, RR, A1)                        # A1 = r_l & r_r
    D.rccx(A1, RT, K1, nb=True)               # K1 = [r = 101] (kappa = 1)
    D.rccx(RL, 0, 3, nb=True)                 # q3 ^= r_l & !n3_c0
    D.cx(RR, A1)                              # A1 = !r_l & r_r
    D.rccx(A1, 2, 3)                          # q3 ^= . & n3_c1
    D.cx(RL, A1)
    D.x(A1)                                   # A1 = !r_l & !r_r
    D.rccx(A1, RT, A2, nb=True)               # A2 = z = [r = 000]
    D.cx(A2, A1)                              # A1 = !r_l & !r_r & r_t
    D.rccx(A1, 6, 3)                          # q3 ^= . & n3_c2
    # tau fix: e1_c ^= h_X (h_b, h_b, h_b^r_r, h_b^r_t), before the controlled H
    D.cx(3, 0)
    D.cx(3, 2)
    D.cx(3, 6)
    D.cx(RR, 6)
    D.cx(3, 8)
    D.cx(RT, 8)
    for q in (2, 6, 8):
        D.x(q)
    for e1, e2, gX, gY in _CORN:
        _cch_rel(D, gX, gY, e1)               # singlet -> basis state; control phases make every coupling +1
    D.cx(9, 13)                               # q13 = delta_c3
    D.cx(5, 9)                                # q9 = delta_c2
    D.cx(1, 5)                                # q5 = delta_c1 (delta_c0 = r_l)
    # closed gadget: (vac_A + vac_B)/sqrt2 -> basis state
    D.cx(0, 2)
    D.cx(0, 6)
    D.cx(0, 8)
    D.x(0)
    D.cch(A2, 1, 0, nb=True)
    # flags (all flip-invariant: relative phases of rccx cancel in the mirror)
    M = _G()
    M.rccx(RL, 12, 0, na=True, nb=True)       # T+- at equal corner c0 -> flip e1_c0
    M.rccx(5, 4, 8, na=True, nb=True)         # c1 -> e1_c3
    M.rccx(9, 10, 0, na=True, nb=True)        # c2 -> e1_c0
    M.rccx(13, 14, 2, na=True, nb=True)       # c3 -> e1_c1
    M.rccx(6, 8, T23, na=True, nb=True)
    M.rccx(T23, 2, T1, nb=True)
    M.rccx(T1, 0, X1, nb=True)                # X1 = all four folded e1 are 0
    M.rccx(12, 4, Y1)
    M.rccx(10, 14, Y2)
    M.rccx(Y1, Y2, Y3)
    M.rccx(Y3, A2, Y4)                        # Y4 = z & e2 = 1111
    # rotation exp(i beta phi X_F), phi = 2 x - x k - 2 x z + 4 sqrt2 x y  (x = X1, k = K1, z = A2, y = Y4), written
    # as 8 Walsh terms whose parities form a Gray cycle (8 CX); in the H basis of F each term is one Rz.
    s2 = math.sqrt(2.0)
    c = {"0": s2 - 0.25, "k": 0.25, "xk": -0.5, "xkz": s2 - 0.5, "xkzy": 0.75 - s2, "xzy": -0.75, "zy": 0.5, "y": 0.5 - s2}
    R = _G()
    F = 1

    def rz(key):
        R.g("rz", F, p=(-2 * beta * c[key],))

    R.g("h", F)
    rz("0")
    R.cx(K1, F)
    rz("k")
    R.cx(X1, F)
    rz("xk")
    R.cx(A2, F)
    rz("xkz")
    R.cx(Y4, F)
    rz("xkzy")
    R.cx(K1, F)
    rz("xzy")
    R.cx(X1, F)
    rz("zy")
    R.cx(A2, F)
    rz("y")
    R.cx(Y4, F)
    R.g("h", F)
    return prep.o + ue.o + D.o + M.o + R.o + _inv(M.o) + _inv(D.o) + _inv(prep.o)


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(10, "work")
    for name, p, qs in _ops(spec.alpha, spec.beta, anc):
        getattr(b, name)(*p, *qs)
    return b
