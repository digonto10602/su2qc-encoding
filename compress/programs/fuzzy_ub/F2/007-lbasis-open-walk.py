"""SUMMARY: r06-F2-006 shared-factor g chain (G = c2 = ~p_t & ~z_r controls swap(q2^1,q2^3), one rccx with ~z_l turns it into the persistent g = ~p_t & (p_r^p_l); c1 = f & ~g controls swap(q2^0,q2^2); c1-uncompute fused with the w01 AND) with the lp wire dropped: all three parity CX come from f (basis r, t, l), so p_r and p_l both sit next to the walk and the 9-term R_x polynomial on (r, t, l, g, w01, w23) runs as an open walk from the constant term to {r, l} whose two closing toggles merge into the leg-2 parity CX (12 CX instead of 14 + no cx(PR,PL) per leg); 86 CX, 11 qubits.
DISCOVERY: exhaustive two-line control search for the (0 2)(1 3) word (32 single-AND branch options, 4608 designs: each line computed by one rccx of wire/line literals, then converted to an invariant or uncomputed by one rccx) with an exact GL(4,2) wire-schedule DP: 144 designs reach the 3-parity-CX floor per leg; the best open walk among them (Held-Karp over all bases and free end sets) is 12 CX, only in basis (p_r, p_t, p_l) with free ends {p_r, p_l} (F2-006 chain included, F3-006 lp basis 13), and IDA* over general CX networks with open ends finds no 11 for any minimal support of the 48 such combinations.
DISCOVERY: for all 2048 valid two-swap branch options the decoded angle function is lambda = [p=3] + k1(p) W + k2(p) V + (-1)^(p_r+p_t+p_l) W V; the options only choose whether W or V carries each of sectors 0,1,2,4,5,7 (64 per decoder); lines reachable by one-rccx conversions have degree <= 2 in (p_r, p_t, p_l), so k0 = [p=3] always costs 4 Walsh terms (9 rotations; every 86-CX variant has 4 rotations at beta, 4 at 2 beta, 1 at 4 beta = 566 gridsynth T at eps 1e-6, invariant under theta -> theta + pi/2).
DISCOVERY: c02 ^ c13 has degree 3 in (f, p_r, p_t, p_l) for every valid control pair, so one line cannot carry both Fredkin controls with a single rccx between them (a 3-rccx-per-leg chain 0 -> c_a -> c_b -> invariant does not exist); 4 rccx per leg stays the floor.
"""
FAMILY = "F2"
PARENT = "r06-F2-006"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7


def q2(i):
    return 2 * i


FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]


def cswap(b, i, j, ctrl):
    """7-CX Clifford+T Fredkin: swap q2^i, q2^j controlled by ctrl."""
    a, d = q2(i), q2(j)
    m = [ctrl, a, d]
    for g in FRED7:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}

# open walk: starts at the empty set (constant term), visits SUPPORT in this order, ends at END = {r, l}; the two
# closing toggles become cz(PR, F), cz(PL, F) after the final H(F) and merge into the leg-2 parity CX (no CX cost)
SUPPORT = [['l'], ['t', 'l', 'w23'], ['r', 't', 'l', 'w23'], ['r', 't', 'l', 'w01', 'w23'], ['r', 't', 'l', 'w01'],
           ['r', 't', 'g', 'w01'], ['r', 'g'], ['r', 'l', 'g']]
END = ['r', 'l']


def group_terms(beta, qm):
    """Exact fit of theta = -4 beta lambda on (r, t, l, w01, w23) with g = ~t & (r ^ l), constant + SUPPORT."""
    sup = [[]] + SUPPORT
    rows, th = [], []
    for r, t, l, x, y in itertools.product(range(2), repeat=5):
        v = dict(r=r, t=t, l=l, w01=x, w23=y, g=(1 - t) & (r ^ l))
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * l]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9
    return {frozenset(qm[n] for n in S): ci for S, ci in zip(sup, c) if abs(ci) > 1e-12}


def walk_open(b, terms, order, t, end):
    """h(t); Rz(const); walk through order (sets of wires); finish at set `end` (not toggled back); h(t)."""
    b.h(t)
    if frozenset() in terms:
        b.rz(terms[frozenset()], t)
    cur = frozenset()
    for S in order:
        for q in sorted(cur ^ S):
            b.cx(q, t)
        cur = S
        b.rz(terms[S], t)
    for q in sorted(cur ^ end):
        b.cx(q, t)
    b.h(t)


def nx(b, qs):
    for q in qs:
        b.x(q)


def rccx_head(b, x, y, t):
    """rccx(x, y -> t) up to (excluding) its final Tdg, H on t (qiskit RCCX decomposition)."""
    b.h(t); b.t(t); b.cx(y, t); b.tdg(t); b.cx(x, t); b.t(t); b.cx(y, t)


def rccx_tail(b, x, y, t):
    """rccx(x, y -> t) from (excluding) its first H, T on t; head(A) + tail(B) = rccx(A) rccx(B) (Tdg H H T = I)."""
    b.cx(y, t); b.tdg(t); b.cx(x, t); b.t(t); b.cx(y, t); b.tdg(t); b.h(t)


def r1(b, G):
    """G ^= ~p_t & ~z_r (PT holds p_t, PR holds raw z_r)."""
    nx(b, [PT, PR]); b.rccx(PT, PR, G); nx(b, [PT, PR])


def r2(b, G):
    """G ^= ~z_l & ~p_t (PL holds raw z_l); first control ~z_l, so the rccx relative phase stays f-independent."""
    nx(b, [PL, PT]); b.rccx(PL, PT, G); nx(b, [PL, PT])


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    a, G, w23 = b.alloc(3, "agw")
    # leg 1
    b.cx(F, PT)                                  # PT = p_t
    r1(b, G)                                     # G = c2 = ~p_t & ~z_r
    cswap(b, 1, 3, G)
    r2(b, G)                                     # G = c2 ^ (~p_t & ~z_l) = ~p_t & (p_r ^ p_l) = g
    b.x(G); b.rccx(F, G, a); b.x(G)              # a = c1 = f & ~g
    cswap(b, 0, 2, a)
    b.x(G); rccx_head(b, F, G, a); b.x(G)        # a = 0 (fused with the w01 AND below)
    b.cx(F, PR); b.cx(F, PL)                     # PR = p_r, PL = p_l (both adjacent to the walk)
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    rccx_tail(b, q2(0), q2(1), a)                # a = w01
    b.rccx(q2(2), q2(3), w23)
    # middle: R_x(F) phase polynomial, open walk
    qm = dict(r=PR, t=PT, l=PL, w01=a, w23=w23, g=G)
    terms = group_terms(beta, qm)
    order = [frozenset(qm[n] for n in S) for S in SUPPORT]
    walk_open(b, terms, order, F, frozenset(qm[n] for n in END))
    b.rccx(q2(2), q2(3), w23)
    rccx_head(b, q2(0), q2(1), a)                # a = 0 (fused with the c1 compute below)
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    # leg 2: cz(k, F) left by the open walk, merged with cx(F, k): cx(F, k) cz(k, F) = sdg(k) cx(F, k) s(k) sdg(F)
    for k in (PL, PR):
        b.sdg(k); b.cx(F, k); b.s(k); b.sdg(F)
    b.x(G); rccx_tail(b, F, G, a); b.x(G)        # a = c1
    cswap(b, 0, 2, a)
    b.x(G); b.rccx(F, G, a); b.x(G)              # a = 0
    r2(b, G)                                     # G = c2
    cswap(b, 1, 3, G)
    r1(b, G)                                     # G = 0
    b.cx(F, PT)
    b.free([a, G, w23])
    return b
