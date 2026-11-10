"""SUMMARY: F2 round 2 on the F1 link-flag GHZ frame (flip qubit F = g_b; corner CX+CCX, 3-way rccx mux for the sector height h_b = direction XOR F, CX tau fix, relative-phase CCH, closed GHZ gadget, 4 rccx folds + NOR bright flag x) with the closed-pair flag cut to y = [e2 = 1111] (3 rccx, no z factor): a 10-term uniformly controlled Rz on F over (x, K1, z, y) walked in 10 CX replaces the 8-term cycle over (x, K1, z, z&y), saving one mirrored rccx (net -4 CX, 9 ancillas); all angles linear in alpha, beta, sqrt2 beta.
DISCOVERY: the closed-pair selector does not need the z factor: with y = [e2 = 1111] alone the angle table on (x, K1, z, y) has a 10-mask Walsh support (masks 0,x,k,xk,z,xz,y,xy,zy,xzy) and a 10-CX Gray walk, so dropping the mirrored rccx (y & z) saves 6 CX for 2 extra CX; minimal supports with y & z need 8 masks / 8 CX, with y split into two pair-ANDs >= 15 masks.
DISCOVERY: the F1 sector height is h_b = f XOR F on every non-closed bright member (f = 1 on the upper member, v in range(W)), in all 7 classes; after Bell maps at c1, c3 the direction is f = NOT([g_b = e1_c1] AND [g_t = e1_c3]), but the tau fix must precede the Bell map, so this does not undercut the mux (post-H tau needs 3-literal controls).
DISCOVERY: a Margolus Toffoli (Ry(-pi/4) CX Ry(-pi/4) CX Ry(pi/4) CX Ry(pi/4)) has its only phase -1 on (c0,c1,t) = (1,0,1), exact on clean targets; used at the corner CCX it leaves a pair sign (-1)^{[diff] not(e2) n3} that is not affine in the frame labels, so the 2-CX CS^dag correction stays.
"""
FAMILY = "F2"
PARENT = "r01-F1-001"

import math

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
_CORN = [(0, 12, 1, 13), (2, 4, 1, 5), (6, 10, 5, 9), (8, 14, 9, 13)]   # (e1, e2, g_X, g_Y) per corner
# Walsh support of the rotation table over the flag bits (x = 1, k = 2, z = 4, y = 8) and its 10-CX Gray walk
_MASKS = (0, 1, 2, 3, 4, 5, 8, 9, 12, 13)
_WALK = (2, 3, 1, 5, 4, 12, 13, 9, 8)


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
        """controlled-controlled-H = Ry(pi/4) CCZ Ry(-pi/4) on t."""
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
    """controlled-controlled-H up to the control phase (-i)^(a b) (4 CX)."""
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


def _walsh():
    """coefficients c_S (units of beta) with phi(x,k,z,y) = sum_S c_S (-1)^(S.p) on every occurring flag pattern:
    phi = 0 if not x; 1 if k (kappa = 1); 2 if not z (kappa = 2); 4 sqrt2 if z and y (closed pair); 0 if z and not y."""
    r2 = 4.0 * math.sqrt(2.0)
    pts, vals = [], []
    for x in (0, 1):
        for k, z in ((0, 0), (1, 0), (0, 1)):
            for y in (0, 1):
                phi = 0.0 if not x else (1.0 if k else (2.0 if not z else (r2 if y else 0.0)))
                pts.append(x | 2 * k | 4 * z | 8 * y)
                vals.append(phi)
    M = np.array([[(-1.0) ** bin(p & m).count("1") for m in _MASKS] for p in pts])
    c = np.linalg.lstsq(M, np.array(vals), rcond=None)[0]
    if np.abs(M @ c - np.array(vals)).max() > 1e-12:
        raise ValueError("Walsh support does not fit the angle table")
    return dict(zip(_MASKS, c.tolist()))


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
        # CX(e1->e2) then CCX(g_X, e2 -> e1) as [CZ.CX merged] + CS^dag(e2, g_X) + rccx (6 CX)
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
    # class selectors and the sector height h_b into q3
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
        _cch_rel(D, gX, gY, e1)               # singlet -> basis state; control phases fix every coupling sign
    D.cx(9, 13)                               # q13 = delta_c3
    D.cx(5, 9)                                # q9 = delta_c2
    D.cx(1, 5)                                # q5 = delta_c1 (delta_c0 = r_l)
    # closed gadget: (vac_A + vac_B)/sqrt2 -> basis state
    D.cx(0, 2)
    D.cx(0, 6)
    D.cx(0, 8)
    D.x(0)
    D.cch(A2, 1, 0, nb=True)
    # flags
    M = _G()
    M.rccx(RL, 12, 0, na=True, nb=True)       # T+- at equal corner c0 -> flip e1_c0
    M.rccx(5, 4, 8, na=True, nb=True)         # c1 -> e1_c3
    M.rccx(9, 10, 0, na=True, nb=True)        # c2 -> e1_c0
    M.rccx(13, 14, 2, na=True, nb=True)       # c3 -> e1_c1
    M.rccx(6, 8, T23, na=True, nb=True)
    M.rccx(T23, 2, T1, nb=True)
    M.rccx(T1, 0, X1, nb=True)                # x = all four folded e1 are 0
    M.rccx(12, 4, Y1)
    M.rccx(10, 14, Y2)
    M.rccx(Y1, Y2, Y3)                        # y = [e2 = 1111] (no z factor)
    # exp(i beta phi(x,k,z,y) X_F): H, uniformly controlled Rz walked over the Walsh masks, H
    coef = _walsh()
    flags = (X1, K1, A2, Y3)
    F = 1
    R = _G()
    R.g("h", F)
    R.g("rz", F, p=(-2.0 * beta * coef[0],))
    cur = 0
    for S in _WALK + (0,):
        for j, q in enumerate(flags):
            if ((cur ^ S) >> j) & 1:
                R.cx(q, F)
        cur = S
        if S:
            R.g("rz", F, p=(-2.0 * beta * coef[S],))
    R.g("h", F)
    return prep.o + ue.o + D.o + M.o + R.o + _inv(M.o) + _inv(D.o) + _inv(prep.o)


def build(spec) -> Builder:
    b = Builder(spec)
    anc = b.alloc(9, "work")
    for name, p, qs in _ops(spec.alpha, spec.beta, anc):
        getattr(b, name)(*p, *qs)
    return b
