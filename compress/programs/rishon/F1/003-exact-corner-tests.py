"""SUMMARY: F1 link-flag GHZ frame (flip qubit F = g_b), parent r02-F1-002 with the fold/NOR flag X1 and the closed-pair check Y1..Y3 replaced by one exact bright test: frame as in the parent (link prep, U_E on L2, corner CX+CCX, r in R2 slots, h_b mux with K1/z selectors, CX tau fix, relative-phase CCH, deltas, closed GHZ gadget; the c3 test literal e1 ^ delta_c3 merged into the tau fix at no cost); flag x = AND_c [e1_c = 0 and (e2_c or delta_c)], closed pair included, from three in-place quadratic tests on the delta registers (delta ^ e2 & !(e1 ^ delta)), corner c2 as the literal !e1 before and after one in-place fold, and a 5-input rccx chain (26 CX per side instead of 30); the uniformly controlled Rz on F needs only 6 Gray-cycle Walsh terms over (x, K1, z); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: in the F1 GHZ frame the bright set is exactly {e1_c = 0 and (e2_c = 1 or delta_c = 1) at all four corners} on all 1296 images, closed pair included (dark passing: 0); the delta registers are 0 in the r = 000 sector, so a test rccx in place on delta_c gives a fresh AND of two e-bits there and four of them isolate the loop among the 256 all-Q images without the 8-bit e2 check.
DISCOVERY: a single-rccx test per corner has an even truth table, so it cannot equal the weight-3 corner condition; the best quadratic tests (delta ^ e2 & !(e1 ^ delta), one CX prep each) leave 16 kappa=1 dark labels that all have e1_c2 = 1, and an exhaustive search (4 tests with z-constant targets, up to 5 CX preps incl. cross-corner sources, plus 0..1 literal, or single-CX kills) finds no cheaper combination; the special c2 corner (literal !e1 read before rccx(!e2, !delta -> e1), then !e1 again) is the cheapest kill.
DISCOVERY: linear test preps e1_c ^= delta_c commute with the frame's CCH (it fires only at Q-Q corners, where delta_c = 0) and with the z-controlled closed gadget, so they can be merged into the tau fix: for c2 and c3 the merge is free (h_r -> h_b ^ r_t, h_t -> h_b ^ r_l), for c1 it costs one CX, for c0 four (the GHZ collapse spreads e1_c0).
"""
FAMILY = "F1"
PARENT = "r02-F1-002"

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
    A1, A2, K1, N1, N2, N3, X1 = anc
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
    D.cx(RL, 8)                               # + delta_c3 = r_t ^ r_l (the c3 test literal e1 ^ delta, merged)
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
    # bright flag X = AND over the corners of [e1_c = 0 and (e2_c = 1 or delta_c = 1)], exact on all 1296 images,
    # the closed pair included: three quadratic tests in place on the delta registers (t = de ^ e2 & !(e1 ^ de)),
    # corner c2 exactly as !e1 & !(e1 ^ !e2 !de) (literal read before the in-place fold)
    M = _G()
    for de, e1, e2 in ((RL, 0, 12), (5, 2, 4)):
        M.cx(de, e1)
        M.rccx(e2, e1, de, nb=True)
    M.rccx(14, 8, 13, nb=True)
    M.rccx(RL, 5, N1)
    M.rccx(N1, 6, N2, nb=True)
    M.rccx(10, 9, 6, na=True, nb=True)
    M.rccx(N2, 13, N3)
    M.rccx(N3, 6, X1, nb=True)
    # rotation exp(i beta phi X_F), phi = x psi(k, z), psi = 2 - k + (4 sqrt2 - 2) z on the occurring (k z = 0)
    # patterns: psi = (1/2 + 2 sqrt2) + 1/2 X_k + (1 - 2 sqrt2) X_z, phi has 6 Walsh terms (one 6-CX Gray cycle)
    s2 = math.sqrt(2.0)
    psi = {"": 0.5 + 2 * s2, "k": 0.5, "z": 1.0 - 2 * s2}
    c = {}
    for key, v in psi.items():
        c[key] = v / 2
        c["x" + key] = -v / 2
    R = _G()
    F = 1
    q_of = {"x": X1, "k": K1, "z": A2}

    R.g("h", F)
    cur = set()
    for key in ("", "k", "xk", "x", "xz", "z"):
        for v in sorted(cur ^ set(key)):
            R.cx(q_of[v], F)
        cur = set(key)
        R.g("rz", F, p=(-2 * beta * c[key],))
    for v in sorted(cur):
        R.cx(q_of[v], F)
    R.g("h", F)
    return prep.o + ue.o + D.o + M.o + R.o + _inv(M.o) + _inv(D.o) + _inv(prep.o)


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(7, "work")
    for name, p, qs in _ops(spec.alpha, spec.beta, anc):
        getattr(b, name)(*p, *qs)
    return b
