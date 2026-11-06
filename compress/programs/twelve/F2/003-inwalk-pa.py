"""SUMMARY: F2 pair frame with in-place flags (parent r02-F2-002) and the pair AND pa = f0 & f1 never stored: in a 10-CX Gray cycle of the 9-term Walsh rotation over (pa, pb, z, t2) pa toggles exactly twice, so both toggles are rccx(f0, f1, F) and the Margolus residual (-1)^(f0 z) (z = net toggle between them) is cancelled by one CZ; CX 119.
DISCOVERY: qiskit's rccx(c0, c1, F) = CCX up to (-1)^(c0 F_in) i^(c0 c1) and is an involution, so two in-walk toggles of the same AND leave exactly (-1)^(c0 L), L = XOR of the walk variables toggled an odd number of times between them; among all 9- and 10-term supports of kappa(pa, pb, z, t) the best in-walk cycle has 10 toggles, pa (or pb) toggled twice and |L| = 1 (z or the other pair AND), never L = {t}, so in-walk costs 10 + 2*2 + 1 = 15 vs 6 + 10 = 16 for a stored pa.
DISCOVERY: the corner flag gadget cx(t, b) + rccx(a, b, t) (4 CX) is minimal among 3-qubit circuits: a numerical search over all 2- and 3-CX skeletons with free single-qubit layers finds no circuit leaving t | (a & ~b) (the flag on the 7 reachable leg/type codes) on any one qubit (residual floors 1.0 and 0.90).
DISCOVERY: with pa in-walk, an exhaustive DFS over multi-target parity networks (CX between F, pb, z, t2 in any direction, rotations on any register, pa toggles on any register, fix cost counted) finds no walk of cost <= 14 for any of the four 9-term supports, so the 15-CX single-target walk is optimal in that model.
"""
FAMILY = "F2"
PARENT = "r02-F2-002"

import itertools

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}


def _kappa(pa, pb, z, t):
    """signed coupling of the frame (None = never occurs): 0 dark, -1 (n1=2), 2 (n1=0), 1/2 (n1=4)"""
    if not (pa and pb):
        return None if (z and t) else 0.0
    return (2.0 if t == 0 else 0.5) if z else -1.0


def _mux_terms():
    pts = list(itertools.product((0, 1), repeat=4))
    supp = [(0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 1), (0, 1, 0, 0), (0, 1, 1, 0),
            (1, 0, 0, 0), (1, 0, 1, 0), (1, 1, 0, 0), (1, 1, 1, 0)]
    rows, rhs = [], []
    for x in pts:
        k = _kappa(*x)
        if k is None:
            continue
        rows.append([(-1) ** sum(s * xi for s, xi in zip(S, x)) for S in supp])
        rhs.append(k)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("support does not reproduce kappa")
    return dict(zip(supp, c))


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f2, z = b.alloc(3, "flags")
    pb, = b.alloc(1, "and")

    def W(a, bb):
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb); g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("s", a)

    def stages(a, bb, j, t, x_on_a):
        if x_on_a:
            g("x", a)
        g("ch", t, a); g("cx", j, a)
        g("x", a); g("ch", t, a); g("x", a); g("s", t)
        if not x_on_a:
            g("x", a)
        g("cx", t, bb); g("x", bb)

    def flag(a, bb, target):
        g("rccx", a, bb, target)

    # relabel the NOT corners (c1 leg q0 by j_b, c3 leg q9 by j_l) while q2, q11 are raw
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 13, tau0); g("cx", 15, tau0)          # t0 from the outer q_j bits of corner 0
    for a, bb in ((1, 10), (0, 4), (3, 6), (7, 9)):
        W(a, bb)
    stages(1, 10, 2, tau0, True)                  # corner 0: t0 = tau0, j_b raw on q2
    g("cx", 5, 11)                                # q11 = j_r ^ j_l
    g("cx", 8, 2)                                 # q2 = j_b ^ j_t
    g("x", 2); g("x", 11); g("rccx", 2, 11, z); g("x", 2); g("x", 11)   # z = [t1 = t2 = t3]
    g("cx", tau0, 2)                              # q2 = j_t ^ j_l = t3
    stages(7, 9, 8, 2, False)                     # corner 3: j_t raw on q8
    flag(7, 9, 2)                                 # q2 = bright_3
    g("cx", tau0, 11)                             # q11 = j_b ^ j_r = t1
    flag(1, 10, tau0)                             # tau0 = bright_0
    stages(0, 4, 5, 11, False)                    # corner 1: control by j_r (raw q5)
    flag(0, 4, 11)                                # q11 = bright_1
    g("cx", 5, 8)                                 # q8 = j_r ^ j_t = t2
    stages(3, 6, 5, 8, False)                     # corner 2: j_r raw on q5
    g("cx", 8, f2); flag(3, 6, f2)                # f2 = bright_2 (q8 keeps t2 for the rotation)
    g("rccx", 2, f2, pb)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # rotation exp(-i beta kappa X_F), kappa(pa, pb, z, t2) as a 9-term Walsh phase polynomial on F; pa = f0 & f1 is
    # never stored: its two toggles are rccx(f0, f1, F) (residual (-1)^(f0 * z), z being the net toggle in between)
    F = 5
    idx = {"pa": 0, "pb": 1, "z": 2, "t": 3}
    reg = {"pb": pb, "z": z, "t": 8}
    coef = _mux_terms()
    seq = ["pb", "pa", "pb", "z", "pb", "pa", "pb+t", "z", "t"]
    b.h(F)
    b.rz(2.0 * spec.beta * coef[(0, 0, 0, 0)], F)
    cur = [0, 0, 0, 0]
    for k, step in enumerate(seq):
        for v in step.split("+"):
            if v == "pa":
                b.rccx(tau0, 11, F)
            else:
                b.cx(reg[v], F)
            cur[idx[v]] ^= 1
        if k < len(seq) - 1:
            b.rz(2.0 * spec.beta * coef[tuple(cur)], F)
    if any(cur):
        raise RuntimeError("walk not closed")
    b.h(F)
    b.cz(tau0, z)

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f2, z]); b.free([pb])
    return b
