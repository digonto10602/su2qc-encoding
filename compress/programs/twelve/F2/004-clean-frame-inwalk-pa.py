"""SUMMARY: F3 5-CX clean corner frame (r03-F3-003) + F2 in-walk pair AND: pa = b0 & b1 is never stored, its two toggles in the 10-CX Gray cycle of the 9-term Walsh rotation over (pa, pb, z, t2) are rccx(b0, b1, F) and the residual (-1)^(b0 z) is one CZ (CX 111).
DISCOVERY: For the F3-frame coupling (kappa = 2, -(-1)^t2, -1/2) the only minimal Walsh supports over (pa, pb, z, t2) have 9 terms (next size 11); with one pair AND in-walk the cheapest cycle is 8 linear toggles + 2 rccx + 1 CZ (15 CX, residual L = {z} or {pb}); a fix-free cycle (pb in-walk with c0 = b2 and L = {t2}, residual (-1)^(b2 t2) = Z(t2) because diff corners are always bright) needs >= 10 linear toggles (>= 16 CX), exhaustive over all 9-term supports and cycles.
DISCOVERY: The three free points (pa & pb = 0, z = t2 = 1) are essential: removing any one of them raises the minimal support from 9 to 12 terms (16 with none), in both the F2 and F3 sign conventions, so no leg-bit proxy for t2 (which is exact only on g = 1) can replace the cx(t2 -> f2) copy.
DISCOVERY: Per-corner sign flips multiply kappa by a character (-1)^(e.t) of the types (the F3 coupling is the F2 coupling times (-1)^t2), which only relabels Walsh terms, so no frame sign choice lowers the 9-term multiplexer.
"""
FAMILY = "F2"
PARENT = "r03-F2-003"

import itertools

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
    """Exact Walsh coefficients on SUPP (free points used)."""
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
    return dict(zip(SUPP, c))


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

    # exp(-i beta kappa(pa, pb, z, t2) X_F) as an exact 9-term Walsh phase polynomial on F = j_r in its X basis;
    # pa = b0 & b1 is never stored: its two toggles are rccx(tau0, q11, F), residual (-1)^(b0 z) fixed by one CZ
    F = 5
    idx = {"pa": 0, "pb": 1, "z": 2, "t": 3}
    reg = {"pb": pb, "z": z, "t": 8}
    coef = _mux_terms()
    seq = ["t", "pb", "pa", "pb", "z", "pb", "pa", "pb+t", "z"]
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
