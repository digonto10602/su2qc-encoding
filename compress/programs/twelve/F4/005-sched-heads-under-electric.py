"""SUMMARY: Same gates as r04-F4-004 (5-CX clean corner frames, 8-CX no-outer-read plumbing, pb stored, 9-term Walsh walk of F = j_b over (pa, pb, z, t2) with pa toggled in-walk, 4 electric phases; CX 111, 13 rotations) rescheduled for depth: the leg-only heads of all four corner frames run under the 167-layer electric rotations, t3 and t2 are formed together before the corner-3/2 frame tails, so depth_CT drops from 1694 to 1672 at equal CX and T.
DISCOVERY: Rotation floor at CX 111 (MILP over the 30 walk-time points, 26 dark flag patterns + 4 bright classes): over (pa, pb, z, t2) plus any extra linear form (type form or single flag) or with z replaced by any AND of two type forms, the minimum Walsh support stays 9; 8 terms need y = z&t2 or pb&z (>= 2 more in-walk rccx), 6 need g = pa&pb, and 4 need {g, z, t2, y} (f = (1/2) g (-1)^t2 - (3/2)(g & ~y)(-1)^(z+t2)), each >= 4 CX more; the electric layer stays 4 rotations even with z or a pair-AND feature, and no electric term merges with the walk since Z_{j_b} anticommutes with X_F.
DISCOVERY: All 10 parity networks of cost 15 on (F, pb, z, t2) with two in-walk rccx on any register and the residual CZ fix counted are single-target into F (exhaustive DFS), so the 9 walk rotations stay serial on one qubit (about 1430 of the depth); path-sum phase folding of the 111-CX circuit finds no T or rotation merges (T_fixed 104 is fold-optimal) and pygridsynth T counts are invariant under pi/2 angle shifts, so T_eps 912 is the floor of this skeleton.
"""
FAMILY = "F4"
PARENT = "r04-F4-004"

import itertools
from fractions import Fraction

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}

# Walsh support over (pa, pb, z, t) (3 free points pa&pb = 0, z = t = 1 used), constant term first
SUPP = [(0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0), (0, 1, 0, 1), (0, 1, 1, 1),
        (1, 0, 0, 1), (1, 0, 1, 1), (1, 1, 0, 1), (1, 1, 1, 1)]
# closed walk through SUPP; pa (index 0) is toggled in-walk, the other three by one CX each
PATH = [(0, 0, 0, 1), (1, 0, 0, 1), (1, 0, 1, 1), (1, 1, 1, 1), (1, 1, 0, 1),
        (0, 1, 0, 1), (0, 1, 1, 1), (0, 0, 1, 0), (0, 0, 0, 0)]


def _kappa(pa, pb, z, t):
    """signed coupling of H_B = kappa X_F in this frame (None = never occurs)."""
    if not (pa and pb):
        return None if (z and t) else 0.0          # dark; (g=0, z=1, t2=1) means n1=4, never dark
    if z:
        return 2.0 if t == 0 else -0.5             # n1 = 0 / n1 = 4
    return -(-1.0) ** t                            # n1 = 2: sign (-1)^(t2 + 1)


def _coef():
    """exact rational Walsh coefficients of kappa on SUPP (checked against every non-free point)"""
    rows, rhs = [], []
    for x in itertools.product((0, 1), repeat=4):
        k = _kappa(*x)
        if k is None:
            continue
        rows.append([(-1) ** sum(s * xi for s, xi in zip(S, x)) for S in SUPP])
        rhs.append(k)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    exact = [Fraction(float(v)).limit_denominator(64) for v in c]
    if np.abs(A @ np.array([float(v) for v in exact]) - rhs).max() > 1e-14:
        raise RuntimeError("support does not reproduce kappa")
    return {S: float(v) for S, v in zip(SUPP, exact)}


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    f3, f2 = b.alloc(2, "flags")
    z, pb = b.alloc(2, "and")

    def head(a, bb):
        """leg-only head of the 5-CX clean corner frame (W_1 up to the T^dg of C_t(T X T^dg))."""
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb)
        g("tdg", a)

    def tail(a, bb, j, t):
        """rest of the frame: type-controlled middle, W_2, C_j(Y_a), C_t(S^dg H S)."""
        g("cx", t, a); g("t", a)                               # C_t(T X T^dg) inside W
        g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("cx", j, a); g("z", a)                               # C_j(Y_a)
        g("ch", t, a); g("sdg", a)                             # C_t(S^dg H S): diff legs off |00>

    def flag(a, bb, target):
        # target holds t: target ^= [legs = 00] gives the bright flag (diff legs never sit on |00>)
        g("x", a); g("x", bb); g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: end leg q0 of link b, c3: end leg q9 of link l); q2, q11 are controls only
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    # electric layer: phase -3/4 alpha per active inner link (q_j bits still raw here)
    for q in (2, 5, 8, 11):
        g("E", q)
    # leg-only frame heads of all four corners (run in parallel with the electric rotations)
    for a, bb in ((7, 9), (3, 6), (1, 10), (0, 4)):
        head(a, bb)
    g("cx", 8, 11)                       # q11 = t3 = j_t ^ j_l
    g("cx", 8, 5)                        # q5 = t2 = j_r ^ j_t (walk type bit)
    tail(7, 9, 8, 11)                    # corner 3: j_t raw on q8
    tail(3, 6, 8, 5)                     # corner 2: j_t raw on q8
    g("cx", 11, f3); flag(7, 9, f3)      # f3 = b3
    g("cx", 5, 11)                       # q11 = u = j_r ^ j_l
    g("cx", 5, f2); flag(3, 6, f2)       # f2 = b2
    g("cx", 2, 8)                        # q8 = v = j_b ^ j_t
    g("x", 8); g("x", 11); g("rccx", 8, 11, z); g("x", 8); g("x", 11)   # z = [all corner types equal]
    g("cx", 5, 8)                        # q8 = t1
    g("cx", 8, 11)                       # q11 = t0
    tail(1, 10, 2, 11); tail(0, 4, 2, 8)  # corners 0, 1: j_b raw on q2
    flag(1, 10, 11)                      # corner 0: q11 = b0 (in place)
    flag(0, 4, 8)                        # corner 1: q8 = b1 (in place)
    g("rccx", f2, f3, pb)                # pb = b2 & b3; pa = b0 & b1 is never stored

    for name, qs in fwd:
        if name == "E":
            b.p(-0.75 * spec.alpha, *qs)
        else:
            getattr(b, name)(*qs)

    # exp(-i beta kappa(pa, pb, z, t2) X_F) as an exact Walsh phase polynomial on F = j_b (q2)
    F = 2
    regs = {1: pb, 2: z, 3: 5}
    c1, c2 = 8, 11                       # in-walk rccx(b1, b0, F): Margolus phase Z_F^b1
    coef = _coef()
    b.h(F)
    b.rz(2.0 * spec.beta * coef[(0, 0, 0, 0)], F)
    cur, inside, net = (0, 0, 0, 0), False, {1: 0, 2: 0, 3: 0}
    for S in PATH:
        lin = [i for i in (1, 2, 3) if S[i] != cur[i]]
        if S[0] != cur[0] and not inside:        # entering the pa = 1 block: linear toggles first
            for i in lin:
                b.cx(regs[i], F)
            b.rccx(c1, c2, F); inside = True
        elif S[0] != cur[0]:                     # leaving: in-walk toggle first
            b.rccx(c1, c2, F); inside = False
            for i in lin:
                b.cx(regs[i], F)
        else:
            for i in lin:
                b.cx(regs[i], F)
                if inside:
                    net[i] ^= 1
        cur = S
        if any(S):
            b.rz(2.0 * spec.beta * coef[S], F)
    b.h(F)
    # the two Z_F^b1 phases straddle the toggles inside the pa block: (-1)^(b1 * net), here net = pb
    for i in (1, 2, 3):
        if net[i]:
            b.cz(c1, regs[i])

    for name, qs in reversed([op for op in fwd if op[0] != "E"]):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([f3, f2]); b.free([z, pb])
    return b
