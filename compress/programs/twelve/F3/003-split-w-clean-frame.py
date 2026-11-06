"""SUMMARY: F2 in-place-flag pipeline with a 5-CX clean corner frame: W's two CX enclose C_t(T X T^dg), then C_j(Y_a) and C_t(S^dg H S) make bright partners equal and send diff legs off |00>, so each corner's bright flag is one rccx onto its type qubit (8 CX per corner instead of 9); U_B is one 9-term Walsh rotation of F=j_r over (pa, pb, z, t2) on a 10-CX Gray cycle (CX 112).
DISCOVERY: A 5-CX clean corner frame exists once a type-controlled gate sits between the two CX of the 2-CX leg map W: [W_1, C_t(T X T^dg)_a, W_2, C_j(Y_a), C_t(S^dg H S)_a] (j = j_A or j_B both work) maps vac and singlet to |00>, dark legs off |00> and every diff partner pair to one common state orthogonal to |00>, so bright_c = t_c ^ [legs=00] is one rccx with no cx(t,b).
DISCOVERY: Template search (CZ-type gates + controlled involutions from t, j_A, j_B, general local layers, least squares from random starts): no 4-gate frame meets the clean-flag conditions; the 5-gate solutions all have the shape (ab, c, [c], ab, c), every W-first template fails; at the NOT corners no 5-gate raw frame exists (1-3 CZ, both leg orientations), so the relabel CX stays, and C_t(S^dg H S) + flag cannot be fused into 3 CX (2-target templates).
DISCOVERY: In this frame the coupling is kappa = 2 (n1=0), -(-1)^{t2} (n1=2), -1/2 (n1=4); with the 3 free points (pa&pb=0, z=t2=1) it has a 9-term Walsh support {0, t, z, pb t, pb z t, pa t, pa z t, pa pb t, pa pb z t} that closes in a 10-CX Gray cycle, the same cost as the F2 sign choice.
"""
FAMILY = "F3"
PARENT = "r02-F2-002"

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
    """Exact Walsh coefficients on SUPP (free points used) and the cheapest closed Gray walk through it."""
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
    coef = dict(zip(SUPP, c))
    best = None
    for perm in itertools.permutations(SUPP[1:]):
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

    # electric layer: phase -3/4 alpha per active inner link (diagonal in the q_j bits)
    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f2, z = b.alloc(3, "flags")
    pa, pb = b.alloc(2, "and")

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
    g("rccx", tau0, 11, pa); g("rccx", 2, f2, pb)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    # exp(-i beta kappa(pa, pb, z, t2) X_F) as an exact Walsh phase polynomial on F = j_r in its X basis
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
