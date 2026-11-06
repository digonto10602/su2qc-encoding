"""SUMMARY: r03-F3-003 (5-CX clean corner frame, in-place bright flags, 9-term Walsh rotation of F=j_r over (pa, pb, z, t2)) with the pair AND pa = b0 & b1 never stored: in the 10-toggle Gray cycle pa toggles exactly twice, both toggles are rccx(b0, b1, F) and the straddled Margolus residual (-1)^(b0 pb) is cancelled by one CZ (walk 15 CX, storage -6): CX 111.
DISCOVERY: F2/F4's in-walk pair AND composes with the 5-CX clean frame and its sign pattern kappa = 2, -(-1)^{t2}, -1/2: the unique Walsh support of size <= 10 (9 terms, every pa/pb term carries t) has 10-toggle cycles with pa (or pb) toggled twice and L = pb (or pa, or z), so walk + fix = 8 + 2*3 + 1 = 15 is the floor (exhaustive over the support, both in-walk choices and all block paths); no cycle has L = {t}, so the free fix Z(t2) via b2 t2 = t2 is out of reach in this frame.
DISCOVERY: At walk time each corner's legs (X-flipped frame) are |11> (same type, bright), |00> or the singlet (|01>-|10>)/sqrt2 (diff type) and |00>, |01>, |10> (dark); separating same from diff on one qubit needs the observable (XX+YY-Z1-Z2)/2, which has operator-Schmidt rank 4, so no <= 1-CX leg map gives a type proxy and the t2 copy into the corner-2 flag ancilla (2 CX) stays.
DISCOVERY: Both pair ANDs in-walk (cycle 0, t, pa t, pa z t, pa pb z t, pa pb t, pb t, pb z t, z with pa and pb toggled twice each) costs 6 linear + 4 rccx = 18 CX but leaves the cubic residual (-1)^(b0 b2 (b1 ^ b3)) (8-CX fix rccx(b0, b2) + 2 CZ + rccx), 26 CX against 15 + 6 for one stored pair AND.
"""
FAMILY = "F3"
PARENT = "r03-F3-003"

import itertools
from fractions import Fraction

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
# Walsh support over (pa, pb, z, t2) of the rotation angle, constant term first
SUPP = [(0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0), (0, 1, 0, 1), (0, 1, 1, 1),
        (1, 0, 0, 1), (1, 0, 1, 1), (1, 1, 0, 1), (1, 1, 1, 1)]


def _kappa(pa, pb, z, t):
    """signed coupling of H_B = kappa X_F in this frame (None = never occurs)."""
    if not (pa and pb):
        return None if (z and t) else 0.0          # dark; (g=0, z=1, t2=1) means n1=4, never dark
    if z:
        return 2.0 if t == 0 else -0.5             # n1 = 0 / n1 = 4
    return -(-1.0) ** t                            # n1 = 2: sign (-1)^(t2 + 1)


def _mux_terms():
    """Exact rational Walsh coefficients of kappa on SUPP (the 3 free points used)."""
    rows, rhs = [], []
    for x in itertools.product((0, 1), repeat=4):
        k = _kappa(*x)
        if k is None:
            continue
        rows.append([(-1) ** sum(s * xi for s, xi in zip(S, x)) for S in SUPP])
        rhs.append(k)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("support does not reproduce kappa")
    exact = [Fraction(float(v)).limit_denominator(64) for v in c]
    if np.abs(A @ np.array([float(v) for v in exact]) - rhs).max() > 1e-14:
        raise RuntimeError("Walsh coefficients are not rationals with denominator <= 64")
    return {S: float(v) for S, v in zip(SUPP, exact)}


# closed Gray cycle 0 -> t -> pa t -> pa z t -> pa pb z t -> pa pb t -> pb t -> pb z t -> z -> 0 (10 toggles);
# pa toggles twice, the net linear toggle between them is pb
WALK = ["t", "pa", "z", "pb", "z", "pa", "z", "pb+t", "z"]


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    # electric layer: phase -3/4 alpha per active inner link (diagonal in the q_j bits)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f2, z = b.alloc(3, "flags")
    pb, = b.alloc(1, "and")

    def frame(a, bb, j, t):
        """5-CX corner frame on legs (a, bb) with type qubit t and one raw link qubit j of this corner."""
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb)
        g("tdg", a); g("cx", t, a); g("t", a)                  # C_t(T X T^dg) inside W
        g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("cx", j, a); g("z", a)                               # C_j(Y_a) (S_a of W cancels against S^dg_a)
        g("ch", t, a); g("sdg", a)                             # C_t(S^dg H S): diff legs end orthogonal to |00>

    def flag(a, bb, target):
        # target holds t: target ^= [legs = 00] gives the bright flag (diff legs never sit on |00>)
        g("x", a); g("x", bb); g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: leg q0 by j_b, c3: leg q9 by j_l) while q2, q11 are raw
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 13, tau0); g("cx", 15, tau0)          # t0 from the outer q_j bits of corner 0
    frame(1, 10, 2, tau0)                         # corner 0: j_b raw on q2
    g("cx", 5, 11)                                # q11 = j_r ^ j_l
    g("cx", 8, 2)                                 # q2 = j_b ^ j_t
    g("x", 2); g("x", 11); g("rccx", 2, 11, z); g("x", 2); g("x", 11)   # z = [t1 = t2 = t3]
    g("cx", tau0, 2)                              # q2 = t3
    frame(7, 9, 8, 2)                             # corner 3: j_t raw on q8
    flag(7, 9, 2)                                 # q2 = bright_3
    g("cx", tau0, 11)                             # q11 = t1
    flag(1, 10, tau0)                             # tau0 = bright_0
    frame(0, 4, 5, 11)                            # corner 1: control j_r (the frame also works with j_B)
    flag(0, 4, 11)                                # q11 = bright_1
    g("cx", 5, 8)                                 # q8 = t2
    frame(3, 6, 5, 8)                             # corner 2: j_r raw on q5
    g("cx", 8, f2); flag(3, 6, f2)                # f2 = bright_2, q8 keeps t2 for the rotation
    g("rccx", 2, f2, pb)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # exp(-i beta kappa(pa, pb, z, t2) X_F) on F = j_r in its X basis; pa = b0 & b1 never stored: its two
    # toggles are rccx(b0, b1, F), residual (-1)^(b0 * L) with L the net linear toggle between them
    F = 5
    idx = {"pa": 0, "pb": 1, "z": 2, "t": 3}
    reg = {"pb": pb, "z": z, "t": 8}
    coef = _mux_terms()
    seq = WALK
    b.h(F)
    b.rz(2.0 * spec.beta * coef[(0, 0, 0, 0)], F)
    cur, inside, net = [0, 0, 0, 0], False, set()
    for k, step in enumerate(seq):
        for v in step.split("+"):
            if v == "pa":
                b.rccx(tau0, 11, F); inside = not inside
            else:
                b.cx(reg[v], F)
                if inside:
                    net ^= {v}
            cur[idx[v]] ^= 1
        if k < len(seq) - 1:
            b.rz(2.0 * spec.beta * coef[tuple(cur)], F)
    if any(cur) or inside:
        raise RuntimeError("walk not closed")
    b.h(F)
    for v in sorted(net):
        b.cz(tau0, reg[v])

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f2, z]); b.free([pb])
    return b
