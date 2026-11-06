"""SUMMARY: Different datapath, no pb register: r04-F3-004's corner pipeline (5-CX clean frames, in-place flags, z, t2 copy) but the pair AND p = b2 & b3 is toggled inside the walk by rccx(b2, b3, F) while b0, b1 stay separate walk registers (b1 ^= b0 before the walk); kappa*g has a 12-term Walsh support over (p, b0, b0^b1, z, t2) once the don't-cares b_c >= t_c and the Gauss rule 'opposite diff corners leave at most one dark corner' are used; the 12-node cycle costs 14 CX + 2 rccx and its straddled Margolus residual is (-1)^(b2 t2) = Z(t2) (no fix CX): CX 112 (one above r04-F3-004's 111), 31 qubits.
DISCOVERY: Fused corner gadget search (frame + in-place flag as one circuit on the legs and the type register, raw j_A/j_B as controls, free U3 layers, local states from the r04 reference): none of the 21870 seven-CX skeletons with one j-controlled CX reaches zero residual (floor 0.028), and none of 17280 eight-CX NOT-corner skeletons with one j_A and one j_B CX does (floor 0.008); a NOT corner cannot use a single j-controlled gate at all because its diff partner relation |01> -> -|00>, |00> -> |10> is not an involution, so 8 CX (normal) and 9 CX (NOT) per corner stay.
DISCOVERY: Dropping the stored pair AND pb: over the 30 choices of (in-walk pair, type bit, per-corner sign convention) that determine kappa (163 of 192 checked), kappa*g has minimum Walsh support 12 (the free points come from b_c >= t_c and the opposite-diff Gauss rule) and the cheapest closed walk is 20 CX after one register CX pair (22) or 24 without, against 15 + 6 with a stored pb; a Margolus residual (-1)^(b2 X) costs nothing when X = t2 because diff corners are always bright.
DISCOVERY: No 2-CX partial Toffoli exists even with don't-cares: |a b t> -> phase |a b, t ^ ab> on the 7 inputs other than |111> (best residual 0.90) or a clean-target AND |a b 0> -> |a b ab> (0.59), so each flag, z and pair AND keeps its 3-CX rccx.
"""
FAMILY = "F3"
PARENT = "r04-F3-004"

import itertools
from fractions import Fraction

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
VARS = ("p", "r0", "r1", "z", "t")          # p = b2 & b3 (in-walk), r0 = b0, r1 = b1 ^ b0, z, t = t2
CYCLE = [(0, 0, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 1, 1, 0), (0, 1, 1, 1, 1), (0, 1, 0, 1, 1),
         (1, 0, 0, 1, 1), (1, 0, 1, 1, 1), (1, 1, 1, 1, 1), (1, 1, 1, 0, 1), (1, 1, 0, 0, 0), (1, 1, 0, 1, 0),
         (0, 0, 0, 1, 0)]


def _kappa(t1, t2, t3):
    t0 = t1 ^ t2 ^ t3
    n1 = t0 + t1 + t2 + t3
    if n1 == 0:
        return 2.0
    if n1 == 4:
        return -0.5
    return -(-1.0) ** t2


def _domain():
    """(register point, Theta/beta) over all physically reachable flag/type patterns."""
    tab = {}
    for t1, t2, t3 in itertools.product((0, 1), repeat=3):
        t0 = t1 ^ t2 ^ t3
        T = (t0, t1, t2, t3)
        for bs in itertools.product((0, 1), repeat=4):
            if any(bs[c] < T[c] for c in range(4)):
                continue                                   # a diff-type corner is always bright
            if T == (1, 0, 1, 0) and bs[1] == 0 and bs[3] == 0:
                continue                                   # opposite diff corners: at most one other dark
            if T == (0, 1, 0, 1) and bs[0] == 0 and bs[2] == 0:
                continue
            val = _kappa(t1, t2, t3) * all(bs)
            key = (bs[2] & bs[3], bs[0], bs[1] ^ bs[0], int(t1 == t2 == t3), t2)
            if key in tab and abs(tab[key] - val) > 1e-12:
                raise RuntimeError("Theta not a function of the walk registers")
            tab[key] = val
    return tab


def _coefs():
    tab = _domain()
    supp = [s for s in CYCLE]
    pts = list(tab)
    A = np.array([[(-1) ** sum(a * b for a, b in zip(S, x)) for S in supp] for x in pts], float)
    rhs = np.array([tab[x] for x in pts])
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("support does not reproduce Theta")
    exact = [Fraction(float(v)).limit_denominator(64) for v in c]
    if np.abs(A @ np.array([float(v) for v in exact]) - rhs).max() > 1e-14:
        raise RuntimeError("coefficients not rational")
    return {S: float(v) for S, v in zip(supp, exact)}


def build(spec):
    b = Builder(spec)
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    for q in (2, 5, 8, 11):
        b.p(-0.75 * spec.alpha, q)

    tau0, f2, z = b.alloc(3, "flags")

    def frame(a, bb, j, t):
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb)
        g("tdg", a); g("cx", t, a); g("t", a)
        g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("cx", j, a); g("z", a)
        g("ch", t, a); g("sdg", a)

    def flag(a, bb, target):
        g("x", a); g("x", bb); g("rccx", a, bb, target)

    g("cx", 2, 0); g("cx", 11, 9); g("z", 0); g("z", 9)
    g("cx", 13, tau0); g("cx", 15, tau0)
    frame(1, 10, 2, tau0)
    g("cx", 5, 11)
    g("cx", 8, 2)
    g("x", 2); g("x", 11); g("rccx", 2, 11, z); g("x", 2); g("x", 11)
    g("cx", tau0, 2)
    frame(7, 9, 8, 2)
    flag(7, 9, 2)                                 # q2 = b3
    g("cx", tau0, 11)
    flag(1, 10, tau0)                             # tau0 = b0
    frame(0, 4, 5, 11)
    flag(0, 4, 11)                                # q11 = b1
    g("cx", 5, 8)
    frame(3, 6, 5, 8)
    g("cx", 8, f2); flag(3, 6, f2)                # f2 = b2, q8 = t2
    g("cx", tau0, 11)                             # q11 = b1 ^ b0 (walk register r1)

    for name, qs in fwd:
        getattr(b, name)(*qs)

    F = 5
    reg = {"r0": tau0, "r1": 11, "z": z, "t": 8}
    coef = _coefs()
    b.h(F)
    cur = CYCLE[0]
    if coef[cur] != 0.0:
        b.rz(2.0 * spec.beta * coef[cur], F)
    inside, net = False, set()
    path = CYCLE[1:] + [CYCLE[0]]
    for k, nxt in enumerate(path):
        diff = [VARS[i] for i in range(5) if cur[i] != nxt[i]]
        lin = [v for v in diff if v != "p"]
        if "p" in diff and not inside:
            b.rccx(f2, 2, F); inside = True
            for v in lin:
                b.cx(reg[v], F); net ^= {v}
        elif "p" in diff and inside:
            b.rccx(f2, 2, F); inside = False
            for v in lin:
                b.cx(reg[v], F)
        else:
            for v in lin:
                b.cx(reg[v], F)
                if inside:
                    net ^= {v}
        cur = nxt
        if k < len(path) - 1:
            b.rz(2.0 * spec.beta * coef[cur], F)
    b.h(F)
    if net == {"t"}:
        b.z(8)                                    # (-1)^(b2 t2) = (-1)^t2: a diff corner is always bright
    else:
        for v in sorted(net):
            b.cz(f2, reg[v])

    for name, qs in reversed(fwd):
        getattr(b, _INV.get(name, name))(*qs)
    b.free([tau0, f2, z])
    return b
