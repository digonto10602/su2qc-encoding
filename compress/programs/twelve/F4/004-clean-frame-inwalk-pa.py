"""SUMMARY: F3's 5-CX clean corner frame (one rccx bright flag per corner) on F4's 8-CX no-outer-read plumbing (flags b0, b1 in place on q11, q8; b2, b3 in ancillas; t2 kept on q5) with only pb = b2&b3 stored; U_B is the 9-term Walsh rotation of F = j_b over (pa, pb, z, t2) for the F3 sign kappa = 2, -(-1)^t2, -1/2 on a closed walk in which pa = b0&b1 is toggled by two in-walk rccx and the straddled phase (-1)^(b1 pb) is cancelled by one CZ: CX 111.
DISCOVERY: The 5-CX clean frame needs no outer read: run in F4's plumbing order (corner 3 with j = j_t raw, corner 2 with j = j_t raw, z, then corners 0 and 1 with j = j_b raw, flags of 0/1 in place) it keeps H_B = kappa X_{j_b} exact on all 433 states with kappa = 2 (n1=0), -(-1)^{t2} (n1=2), -1/2 (n1=4), so 8 plumbing CX replace F3's 6 + 2 outer reads at equal cost.
DISCOVERY: For the F3 sign kappa the support {0, t, z, pb t, pb z t, pa t, pa z t, pa pb t, pa pb z t} has an in-walk pa cycle 0 -t- [pa] -z-pb-z- [pa] -z- (pb,t) -z- 0 with 8 linear toggles and net = pb inside the pa block, so pa costs 2 rccx + 1 CZ (walk 15 CX) instead of a stored pa (6) + 10-CX cycle: 48 forward CX per side, total 111.
DISCOVERY: In the clean frame diff-type bright corners leave each leg bit at probability 1/4 and dark corners at 1/3 (only same-type bright legs are a basis state), so no leg bit is a type proxy and t2 must stay on q5; by count a (g, z, t) mux with stored pa, pb and in-walk g is 2 x 51 + 11 = 113 CX in this frame (and needs 7 terms for the (-1)^t2 sign; single Pauli insertions on corners 0/1 did not make the n1=2 sign constant), 2 CX more than the 9-rotation in-walk-pa walk.
"""
FAMILY = "F4"
PARENT = "r03-F4-003"

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

    # electric layer: phase -3/4 alpha per active inner link (diagonal in the q_j bits)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    f3, f2 = b.alloc(2, "flags")
    z, pb = b.alloc(2, "and")

    def frame(a, bb, j, t):
        """5-CX clean corner frame on legs (a, bb) with type qubit t and one raw link qubit j."""
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb)
        g("tdg", a); g("cx", t, a); g("t", a)                  # C_t(T X T^dg) inside W
        g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("cx", j, a); g("z", a)                               # C_j(Y_a)
        g("ch", t, a); g("sdg", a)                             # C_t(S^dg H S): diff legs off |00>

    def flag(a, bb, target):
        # target holds t: target ^= [legs = 00] gives the bright flag (diff legs never sit on |00>)
        g("x", a); g("x", bb); g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: end leg q0 of link b, c3: end leg q9 of link l)
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 8, 11)                       # q11 = t3 = j_t ^ j_l
    frame(7, 9, 8, 11)                   # corner 3: j_t raw on q8
    g("cx", 11, f3); flag(7, 9, f3)      # f3 = b3
    g("cx", 8, 5)                        # q5 = t2 = j_r ^ j_t (walk type bit)
    g("cx", 5, 11)                       # q11 = u = j_r ^ j_l
    frame(3, 6, 8, 5)                    # corner 2: j_t raw on q8
    g("cx", 5, f2); flag(3, 6, f2)       # f2 = b2
    g("cx", 2, 8)                        # q8 = v = j_b ^ j_t
    g("x", 8); g("x", 11); g("rccx", 8, 11, z); g("x", 8); g("x", 11)   # z = [all corner types equal]
    g("cx", 5, 8)                        # q8 = t1
    g("cx", 8, 11)                       # q11 = t0
    frame(1, 10, 2, 11); flag(1, 10, 11)  # corner 0: q11 = b0 (in place)
    frame(0, 4, 2, 8); flag(0, 4, 8)      # corner 1: q8 = b1 (in place)
    g("rccx", f2, f3, pb)                # pb = b2 & b3; pa = b0 & b1 is never stored

    for name, qs in fwd:
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

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([f3, f2]); b.free([z, pb])
    return b
