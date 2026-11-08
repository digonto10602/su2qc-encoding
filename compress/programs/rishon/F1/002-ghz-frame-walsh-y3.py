"""SUMMARY: F1 link-flag GHZ frame (flip qubit F = g_b), parent r01-F1-001 with the closed-pair flag Y4 = z & [e2=1111] removed: frame (link prep, U_E on L2, corner CX+CCX, r in R2 slots, h_b mux with K1/z selectors, CX tau fix before relative-phase CCH, deltas, closed GHZ gadget) and the four rccx folds + NOR ladder X1 as in the parent; the uniformly controlled Rz on F now reads y = Y3 = [e2=1111] directly with 10 Gray-cycle Walsh terms over (x, k, z, y) instead of 8 terms + one rccx pair (-4 CX, one ancilla fewer); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the closed-pair flag needs no AND with z: psi = 2 - k - 2z + 4 sqrt2 z y equals (1/2+sqrt2) + 1/2 X_k + (1-sqrt2) X_z - sqrt2 X_y + sqrt2 X_z X_y (X_v = (-1)^v) on all occurring patterns (k z = 0), so phi = x psi is 10 Walsh terms in one Gray cycle (10 CX); an exhaustive search over supports of up to 9 terms finds none, so 10 is the minimum for (x, k, z, y); L1-sparse fits replacing K1 by r bits (~28 CX), Y3 by (Y1, Y2) (~20 CX) or X1 by (T1, e1_c0) (~18 CX) cost more than the rccx pair they save.
DISCOVERY: every qubit other than F must be flip-invariant on bright images while the rotation acts: dropping the R2_b zeroing (CX(R1->R2), CX(g_b->R2)) or the delta CX(g_b->g_r) (even with delta_c1 read from the r_r slot) leaves a copy of g_b in the register and breaks D^dagger (leak ~1), so the 8 R2 CX and 3 delta CX of the frame are the minimum.
"""
FAMILY = "F1"
PARENT = "r01-F1-001"

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
    A1, A2, K1, T23, T1, X1, Y1, Y2, Y3 = anc
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
    # rotation exp(i beta phi X_F), phi = x psi(k, z, y) with x = X1, k = K1, z = A2, y = Y3 = [e2 = 1111]:
    # psi = 2 - k - 2 z + 4 sqrt2 z y; on the occurring patterns (k z = 0) psi has 5 Walsh terms
    # psi = (1/2 + sqrt2) + 1/2 X_k + (1 - sqrt2) X_z - sqrt2 X_y + sqrt2 X_z X_y  (X_v = (-1)^v), x = (1 - X_x)/2,
    # so phi has 10 Walsh terms, visited as a Gray cycle (10 CX); in the H basis of F each term is one Rz.
    s2 = math.sqrt(2.0)
    psi = {"": 0.5 + s2, "k": 0.5, "z": 1.0 - s2, "y": -s2, "zy": s2}
    c = {}
    for key, v in psi.items():
        c[key] = v / 2
        c["x" + key] = -v / 2
    R = _G()
    F = 1
    q_of = {"x": X1, "k": K1, "z": A2, "y": Y3}

    R.g("h", F)
    cur = set()
    for key in ("", "k", "xk", "x", "xz", "z", "zy", "xzy", "xy", "y"):
        for v in sorted(cur ^ set(key)):
            R.cx(q_of[v], F)              # F now carries F ^ parity(key)
        cur = set(key)
        R.g("rz", F, p=(-2 * beta * c[key],))
    for v in sorted(cur):
        R.cx(q_of[v], F)                  # close the cycle
    R.g("h", F)
    return prep.o + ue.o + D.o + M.o + R.o + _inv(M.o) + _inv(D.o) + _inv(prep.o)


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(9, "work")
    for name, p, qs in _ops(spec.alpha, spec.beta, anc):
        getattr(b, name)(*p, *qs)
    return b
