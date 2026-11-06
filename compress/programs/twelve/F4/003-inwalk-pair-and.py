"""SUMMARY: F4-002 frame and 8-CX plumbing (no outer reads; flags b0, b1 in place on q11, q8, flags b2, b3 in ancillas) with only pb = b2&b3 stored; U_B is F2's 9-term Walsh rotation of F = j_b over (pa, pb, z, t2) on a closed Gray walk in which pa = b0&b1 is toggled by two in-walk rccx (no pa register) and the straddled Margolus phase (-1)^(b1 pb) is cancelled by one CZ: CX 119.
DISCOVERY: One pair AND of the bright tree can live inside the 9-term (pa, pb, z, t) Walsh walk: toggling F twice with rccx(b0, b1, F) leaves Z_F^b1 phases that only straddle the toggles between them, i.e. (-1)^(b1 * net) with net = pb on the best walk, fixed by one CZ; this drops the pa register (6 CX) for +4 walk CX +1 CZ. Exhaustive over all 9- and 11-term supports and Gray cycles with pa (or pb) toggled twice: linear toggles + fixes >= 9 (walk 15 CX); fix-free walks (net = t, using b_c t_c = t_c so the residual is a plain Z) need 10 linear toggles.
DISCOVERY: Both pair ANDs in-walk cannot be made residual-free: a nested pa/pb interval structure would need every pb-carrying Walsh term to share one pa value, which contradicts kappa (kappa(pa=1, pb=1) - kappa(pa=1, pb=0) = k(z,t) != 0 while the pa=0 difference is 0), so interleaving leaves a cubic phase b_a b2 b3 + b_c b0 b1.
DISCOVERY: The walk type bit may be any register equal to the common corner type when z = 1 (kappa is t-independent at z = 0), but at walk time no leg bit is a type proxy (same-type bright legs are (1,1), diff and dark legs both span {00, 01, 10}), so 4 flags + 1 type need 2 ancilla loads besides the 6 distinct fold forms (t0..t3, u, v): 8 plumbing CX per side stays the floor in this frame.
"""
FAMILY = "F4"
PARENT = "r02-F4-002"

import itertools
from fractions import Fraction

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}

# Walsh support over (pa, pb, z, t) (3 free points pa&pb = 0, z = t = 1 used) and a closed Gray walk;
# pa (index 0) is toggled in-walk, the other three variables are registers toggled by one CX each.
SUPP = [(0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 1), (0, 1, 0, 0), (0, 1, 1, 0),
        (1, 0, 0, 0), (1, 0, 1, 0), (1, 1, 0, 0), (1, 1, 1, 0)]
PATH = [(0, 0, 0, 1), (0, 0, 1, 1), (0, 1, 1, 0), (0, 1, 0, 0), (1, 1, 0, 0),
        (1, 1, 1, 0), (1, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 0)]


def _kappa(pa, pb, z, t):
    """signed coupling of the frame (None = never occurs): 0 dark, -1 (n1=2), 2 (n1=0), 1/2 (n1=4)"""
    if not (pa and pb):
        return None if (z and t) else 0.0
    return (2.0 if t == 0 else 0.5) if z else -1.0


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

    def corner(a, bb, jA, t, target, x_on_a):
        # W: 2-CX map |00>->|00>, Psi- -> |10>, Psi+ -> |01>, |11> -> -|11> on the two legs
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb); g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("s", a)
        if x_on_a:
            g("x", a)  # flips the sign of the diff partner map at this corner only
        # type-selected canonicalisation (diff Z_a -> X_a), partners made equal by C_jA(X_a)
        g("ch", t, a); g("cx", jA, a)
        g("x", a); g("ch", t, a); g("x", a); g("s", t)
        if target != t:
            g("cx", t, target)
        # bright flag: target ^= [same-type bright legs] (never on diff legs); target holds t first
        if not x_on_a:
            g("x", a)
        g("cx", t, bb); g("x", bb)
        g("rccx", a, bb, target)

    # relabel the two NOT corners (c1: end leg q0 of link b, c3: end leg q9 of link l)
    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 8, 11)                       # q11 = t3 = j_t ^ j_l
    corner(7, 9, 8, 11, f3, False)       # corner 3 -> f3 = b3
    g("cx", 8, 5)                        # q5 = t2 = j_r ^ j_t (walk type bit)
    g("cx", 5, 11)                       # q11 = u = j_r ^ j_l
    corner(3, 6, 8, 5, f2, False)        # corner 2 -> f2 = b2
    g("cx", 2, 8)                        # q8 = v = j_b ^ j_t
    g("x", 8); g("x", 11); g("rccx", 8, 11, z); g("x", 8); g("x", 11)   # z = [all corner types equal]
    g("cx", 5, 8)                        # q8 = t1
    g("cx", 8, 11)                       # q11 = t0
    corner(1, 10, 2, 11, 11, True)       # corner 0: q11 = b0 (in place)
    corner(0, 4, 2, 8, 8, False)         # corner 1: q8 = b1 (in place)
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
