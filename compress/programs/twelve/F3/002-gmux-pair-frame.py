"""SUMMARY: F2 pair frame (2-CX leg frame W, C_t(H), C_jA(X), C_t(YH), cx(t,b), one rccx bright flag per corner, AND tree g) without the z flag: one 11-term Walsh-multiplexed X rotation of F over (g, t1, t2, t2^t3), 12-CX Gray walk after one extra fold CX (CX 124).
DISCOVERY: g*kappa(t) (kappa = 2, -1, 1/2 for n1 = 0, 2, 4; kappa*g = -g + 3[n1=0 and bright] + 1.5[n1=4]) has an 11-term Walsh support over (g, t1, t2, t3) via the free point (g=0, n1=4); in the basis (t1, t2, t2^t3) it is Gray-walked with 12 CX (plain basis: 16-CX walk, and an exhaustive parity-network search finds no 12-CX network), so the type dependence costs 12+2 CX instead of z (10) + (g, z, t) mux (6).
DISCOVERY: Trading AND depth, t copies and multiplexer terms is CX-neutral: (g; t) 18+6+14, (b0b1b2, b3; t) 12+6+20, (b0b1, b2b3; t) 12+6+20, (b0b1b2, x3; t) 12+4+22, raw (x0..x3; t) 0+0+~38 (24 terms) all total 38 CX; t provisioning (fold + copies + outer t0) is >= 9 CX per side for every 12-walk basis (exhaustive over <= 5 fold CX).
DISCOVERY: No frame W (2 CX) followed by sector-controlled local corrections maps all diff legs into a product subspace u(x)C^2 (W|00>, W|01>, W|10> would share a 2-dim space): no leg proxy for t_c and no leg-only NOR dark flag; with W first, no 5-gate (2 CX + 3 controlled involutions on jA/jB/t) clean frame was found (numerical search over all 192 templates), so F2's 6-gate clean corner is kept.
"""
FAMILY = "F3"
PARENT = "r01-F3-001"

import itertools

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
F = 2                      # flip qubit after the fold: q2 = j_b
# Walsh support of the rotation angle over (g, q5 = t1, q8 = t2, q11 = t2^t3), constant term first, Gray-walk order
WALK = [(1, 0, 0, 0), (1, 0, 0, 1), (0, 0, 0, 1), (0, 1, 0, 1), (0, 1, 0, 0), (0, 1, 1, 0), (1, 1, 1, 0), (1, 1, 1, 1),
        (0, 1, 1, 1), (0, 0, 1, 1), (0, 0, 1, 0)]


def kappa(t):
    """Signed coupling of H_B = kappa * g * X_F in this frame (n1 = number of corners of different type)."""
    return {0: 2.0, 2: -1.0, 4: 0.5}[sum(t)]


def mux_coefficients():
    """Exact Walsh coefficients c_S with sum_S c_S (-1)^{S.x} = g * kappa(t) on every reachable (g, t)."""
    supp = [(0, 0, 0, 0)] + WALK
    rows, rhs = [], []
    for t123 in itertools.product((0, 1), repeat=3):
        t = (t123[0] ^ t123[1] ^ t123[2],) + t123
        y = (t[1], t[2], t[2] ^ t[3])
        for g in (0, 1):
            if g == 0 and sum(t) == 4:
                continue          # never occurs: with all four corners of different type no corner can be dark
            rows.append([(-1) ** sum(a * b for a, b in zip(S, (g,) + y)) for S in supp])
            rhs.append(kappa(t) * g)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("Walsh support does not reproduce g*kappa")
    return c


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    # electric layer: phase -3/4 alpha per active inner link (diagonal in the q_j bits)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f1, f2, f3 = b.alloc(4, "flags")
    pa, pb, gg = b.alloc(3, "and")

    def corner(a, bb, jA, t, target, x_on_a):
        # W: 2-CX Clifford+T leg map |00>->|00>, Psi- -> |10>, Psi+ -> |01>, |11> -> -|11>
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb); g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("s", a)
        if x_on_a:
            g("x", a)      # flips the diff partner sign at this corner: kappa = -1 on every n1 = 2 pair
        g("ch", t, a); g("cx", jA, a)                          # partners equal except the j bits
        g("x", a); g("ch", t, a); g("x", a); g("s", t)         # C_t(YH): diff legs avoid one code
        if target != t:
            g("cx", t, target)
        if not x_on_a:
            g("x", a)
        g("cx", t, bb); g("x", bb)
        g("rccx", a, bb, target)                               # target = t ^ [same-type bright legs] = bright flag

    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)     # relabel the two NOT corners (c1, c3)
    g("cx", 13, tau0); g("cx", 15, tau0)                   # t0 from the outer links of corner 0
    g("cx", 8, 11)                                         # q11 = t3
    corner(7, 9, 8, 11, f3, False)
    g("cx", 5, 8)                                          # q8 = t2
    corner(3, 6, 5, 8, f2, False)
    g("cx", 2, 5)                                          # q5 = t1, q2 = F = j_b
    corner(0, 4, 2, 5, f1, False)
    corner(1, 10, 2, tau0, tau0, True)
    g("rccx", tau0, f1, pa); g("rccx", f2, f3, pb); g("rccx", pa, pb, gg)   # g = no dark corner
    g("cx", 8, 11)                                         # q11 = t2 ^ t3 (multiplexer basis)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # exp(-i beta g kappa(t) X_F) as an exact Walsh phase polynomial on F in its X basis
    ctrl = (gg, 5, 8, 11)
    c = mux_coefficients()
    b.h(F)
    b.rz(2.0 * spec.beta * float(c[0]), F)
    cur = (0, 0, 0, 0)
    for S, w in zip(WALK, c[1:]):
        for i in range(4):
            if S[i] != cur[i]:
                b.cx(ctrl[i], F)
        cur = S
        b.rz(2.0 * spec.beta * float(w), F)
    for i in range(4):
        if cur[i]:
            b.cx(ctrl[i], F)
    b.h(F)

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f1, f2, f3]); b.free([pa, pb, gg])
    return b
