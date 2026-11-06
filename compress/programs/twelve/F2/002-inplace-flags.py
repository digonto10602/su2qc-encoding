"""SUMMARY: F2 pair frame with in-place flags: a fold schedule (cx 5>11, 8>2 give z's inputs, tau0>2, tau0>11, 5>8 give t3, t1, t2 just in time) writes three corner bright flags onto the type qubits themselves (F = j_r), and the AND gg is dropped: U_B is one 9-term Walsh rotation of F over (pa, pb, z, t2) on a 10-CX Gray cycle.
DISCOVERY: fold schedule search (Dijkstra over CX folds, corner steps t->j->t, in-place or copied flags, z from two pair differences): 6 CX per side for fold + z inputs + flag targets is optimal with t0 from the outer bits (parent 8); corner 1 may take cx(j_B, a) instead of cx(j_A, a) since the diff legs then differ only by a Z_a phase; with no outer reads no schedule of total cost <= 7 was found (search limited to folds whose qubits hold raw j, corner types or pair differences).
DISCOVERY: without gg the rotation angle kappa(pa&pb, z, t) has minimum Walsh support 9 over (pa, pb, z, t) using the 3 free points (pa&pb=0, z=t=1); every 9-term support needs a 10-CX Gray cycle (parity imbalance), so dropping the top AND saves 2 CX for 3 extra rotations; dropping pb as well needs 20 terms.
DISCOVERY: negative results: after the 2-CX frame W no t-controlled sequence of <=3 CX (1q involutions, C_t(XX), rccx(t,.)) puts all diff legs on an affine line, so an outer AND dark bit cannot replace the flag rccx; at the NOT corners no frame L2 W L1 (local Cliffords) with a single j-controlled X exists, the relabel CX is needed.
"""
FAMILY = "F2"
PARENT = "r01-F2-001"

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
    """Walsh coefficients on the 9-term support (3 free values used) and a 10-CX Gray cycle through it."""
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
    coef = dict(zip(supp, c))
    nodes = supp[1:]
    best = None
    for perm in itertools.permutations(nodes):
        path = [(0, 0, 0, 0)] + list(perm) + [(0, 0, 0, 0)]
        cost = sum(sum(a ^ b for a, b in zip(p, q)) for p, q in zip(path, path[1:]))
        if best is None or cost < best[0]:
            best = (cost, path[1:])
    return coef, best[1]


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f2, z = b.alloc(3, "flags")
    pa, pb = b.alloc(2, "and")

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
    g("rccx", tau0, 11, pa); g("rccx", 2, f2, pb)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # rotation exp(-i beta kappa X_F) with kappa = kappa(g = pa & pb, z, t2) as an exact Walsh phase polynomial on F
    F = 5
    bits = (pa, pb, z, 8)
    coef, walk = _mux_terms()
    b.h(F)
    b.rz(2.0 * spec.beta * coef[(0, 0, 0, 0)], F)
    cur = (0, 0, 0, 0)
    for S in walk:
        for i in range(4):
            if S[i] != cur[i]:
                b.cx(bits[i], F)
        cur = S
        if any(S):
            b.rz(2.0 * spec.beta * coef[S], F)
    b.h(F)

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f2, z]); b.free([pa, pb])
    return b
