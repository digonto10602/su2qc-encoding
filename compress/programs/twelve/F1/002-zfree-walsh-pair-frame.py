"""SUMMARY: F2 pair frame (2-CX leg frame, C_t(H) C_jA(X) C_t(YH) per corner, t-preloaded rccx bright flags, 3-rccx AND) without the z flag: U_B is one 11-term Walsh multiplexed X rotation of F over (g, t1, t2, t1^t3), Gray-walked with 12 CX plus one CX(t1->t3) before and after (CX 124, reads 2 outer bits).
DISCOVERY: g*kappa(t) (kappa = 2, -1, 1/2 for n1 = 0, 2, 4; free at g=0, n1=4) has minimum Walsh support 11 in every basis of the three type bits, but its cheapest closed Gray walk is 16 CX when the controls are three pure corner types and 12 CX once one control is a pair sum (t1^t3); a CX before/after the multiplexer makes the z-free rotation 14 CX vs 16 for the z flag (5+5) plus 6-CX mux; an exhaustive fold search shows a fold leaving a non-pure basis costs 1 CX more (9 vs 8), and two pair sums plus a type (for z) cost 10.
DISCOVERY: NOT corners need two j-controlled operations (the relabel is not removable in the W + controlled-slot family): there the diff partners map |00> -> |10> and |01> -> |00> with one common phase, so Omega_11^-1 Omega_10 squares to a non-identity on |01> and cannot be one W-conjugated reflection; on the copy corners a single jA fix plus two t-controlled 1q gates also fails in every order (fix first forces the same-type and diff partner maps to coincide; otherwise the flag code cannot be avoided).
DISCOVERY: Numerically (least squares over all 1q layers, 512 skeletons) no corner frame [3-CX leg unitary + 2 controlled 1q slots from t, not-t, jA, jB] gives partner equality plus a single-AND t-preloaded flag (residual floor 1.35), so the F2 corner (6 CX + rccx) is locally optimal in that family.
"""
FAMILY = "F1"
PARENT = "r01-F2-001"

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}

# Walsh support of the multiplexed angle over the controls (g, q5 = t1, q8 = t2, q11 = t1^t3), listed in the order
# of a closed 12-CX Gray walk (each step flips one control); the constant term is applied first.
WALK = [(1, 0, 0, 0), (1, 0, 0, 1), (0, 0, 0, 1), (0, 1, 0, 1), (0, 1, 0, 0), (0, 1, 1, 0), (1, 1, 1, 0),
        (1, 1, 1, 1), (0, 1, 1, 1), (0, 0, 1, 1), (0, 0, 1, 0)]


def kappa(g, t1, t2, t3):
    """Signed coupling of the bright pair in this frame (H_B = kappa * X_F); 0 on dark states (g = 0)."""
    t0 = t1 ^ t2 ^ t3
    n1 = t0 + t1 + t2 + t3
    if not g:
        return None if n1 == 4 else 0.0        # g = 0 never occurs with four diff-type corners (free point)
    return {0: 2.0, 2: -1.0, 4: 0.5}[n1]


def walsh_coefficients():
    """Exact coefficients c_S with sum_S c_S (-1)^(S.y) = kappa on every occurring control pattern y."""
    supp = [(0, 0, 0, 0)] + WALK
    rows, rhs = [], []
    for g in (0, 1):
        for t1, t2, t3 in np.ndindex(2, 2, 2):
            k = kappa(g, t1, t2, t3)
            if k is None:
                continue
            y = (g, t1, t2, t1 ^ t3)
            rows.append([(-1) ** sum(a * b for a, b in zip(S, y)) for S in supp])
            rhs.append(k)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("Walsh support does not reproduce kappa")
    return c


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    # electric layer U_E(alpha): phase -3/4 alpha per active inner link (first in the circuit)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f1, f2, f3 = b.alloc(4, "flags")
    pa, pb, gg = b.alloc(3, "and")

    def corner(a, bb, jA, t, target, x_on_a):
        # W: 2-CX Clifford+T leg frame |00>->|00>, Psi- -> |10>, Psi+ -> |01>, |11> -> -|11>
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb); g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("s", a)
        if x_on_a:
            g("x", a)       # flips the diff partner sign at this corner: kappa = -1 on every n1 = 2 pair
        # type-selected canonicalisation (diff Z_a -> X_a), partner fix C_jA(X_a), second type gate C_t(YH)
        g("ch", t, a); g("cx", jA, a)
        g("x", a); g("ch", t, a); g("x", a); g("s", t)
        if target != t:
            g("cx", t, target)                      # preload the flag with t_c
        # bright flag: target = t ^ [legs = same-bright code] (diff legs never hit the t-shifted code)
        if not x_on_a:
            g("x", a)
        g("cx", t, bb); g("x", bb)
        g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: end leg q0 of link b, c3: end leg q9 of link l)
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 13, tau0); g("cx", 15, tau0)          # t0 from the outer e bits of corner 0
    g("cx", 8, 11)                               # q11 = t3
    corner(7, 9, 8, 11, f3, False)
    g("cx", 5, 8)                                # q8 = t2
    corner(3, 6, 5, 8, f2, False)
    g("cx", 2, 5)                                # q5 = t1 ; q2 = F = j_b
    corner(0, 4, 2, 5, f1, False)
    corner(1, 10, 2, tau0, tau0, True)           # corner 0 consumes tau0 as its flag
    g("rccx", tau0, f1, pa); g("rccx", f2, f3, pb); g("rccx", pa, pb, gg)   # g = all corners bright

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # U_B: exp(-i beta kappa(g, t) X_F) as a Walsh phase polynomial on F in its X basis
    F = 2
    ctrl = (gg, 5, 8, 11)
    coef = walsh_coefficients()
    b.cx(5, 11)                                  # q11 = t1 ^ t3 (one pair-sum control)
    b.h(F)
    b.rz(2.0 * spec.beta * float(coef[0]), F)
    cur = (0, 0, 0, 0)
    for S, c in zip(WALK + [(0, 0, 0, 0)], list(coef[1:]) + [None]):
        for i in range(4):
            if S[i] != cur[i]:
                b.cx(ctrl[i], F)
        cur = S
        if c is not None:
            b.rz(2.0 * spec.beta * float(c), F)
    b.h(F)
    b.cx(5, 11)

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f1, f2, f3]); b.free([pa, pb, gg])
    return b
