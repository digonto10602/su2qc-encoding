"""SUMMARY: g-line-free two-swap frame: the (0 2) control c02 = ~lp & s_t (one rccx) is converted after its Fredkin by U ^= f & ~lp into the invariant line u = p_t & ~lp, which both feeds the (1 3) control ~(s_r & ~u) (one rccx) and serves as the g-class middle variable, so the persistent g line disappears (control cost 24 instead of 30 CX); R_x polynomial (8 terms + constant, 9 rotations) on (r, lp, t, u, w01, w23) with an open walk whose closing r toggle merges into the leg-2 parity CX (13 CX); 87 CX, 11 qubits.
DISCOVERY: a Fredkin control line c = u(p) xor f*b(p) need not be uncomputed before the middle: one rccx(f, b) converts it to the invariant u(p), and with c0 = f the rccx relative phases of the chain 0 -> c -> u multiply to i^(p_t & ~lp), a function of the parity sector only, so they cancel between the mirrored legs; for 32 of the 128 cheap two-swap branch patterns u is in the g class t(r+l)+affine, and for 4 of them (2 per decoder; here decoder (0,1),(2,3) with c02 = ~lp & s_t, c13 = ~(s_r & ~u)) both controls are single literal ANDs.
DISCOVERY: the parity CX(f -> p_k) next to the walk's H(f) absorbs one walk toggle of p_k at each end (h cx(k->f) = cz(k,f) h, and cx(f->k) cz = sdg(k) cx s(k) s(f)), so the phase polynomial is an open walk from/to subsets of {p_r, p_t}; with the constant term (sector-3 indicator) it costs 13 CX (IDA* over general CX networks with open ends: 13 optimal for this support), 12 without the constant.
DISCOVERY: with p_l instead of lp on the q1 wire the same support has an open walk of 11 CX, but lp is needed on a wire for both U toggles, which costs one more parity CX per leg (tie at 87).
"""
FAMILY = "F3"
PARENT = "r05-F3-005"
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
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 0, 1, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 1, 0, -1)}

# walk order (open walk: starts at the empty set, ends at {r}; the closing r toggle merges into the leg-2 parity CX)
SUPPORT = [['t', 'u'], ['r', 't', 'u'], ['lp', 'r', 't', 'u', 'w23'], ['lp', 't', 'w23'], ['lp', 't', 'w01', 'w23'],
           ['lp', 't', 'w01'], ['lp', 'r', 'w01'], ['r']]


def group_terms(beta, qm):
    sup = [[]] + SUPPORT
    rows, th = [], []
    for r, lp, t, x, y in itertools.product(range(2), repeat=5):
        v = dict(r=r, lp=lp, t=t, w01=x, w23=y, u=t & (1 - lp))
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * (lp ^ r)]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9
    return {frozenset(qm[n] for n in S): ci for S, ci in zip(sup, c) if abs(ci) > 1e-12}


def leg(b, U, A):
    """routing leg as a list of self-inverse blocks (leg 2 = the same blocks in reverse order).

    Wires: F = f, PR = s_r (raw until blk_par), PT = s_t (raw until blk_par), PL = lp = s_r ^ s_l after blk_lp.
    U: 0 -> c02 = ~lp & s_t (control of swap(0,2)) -> u = p_t & ~lp (invariant, kept through the middle).
    A: 0 -> s_r & ~u -> 0; the swap(1,3) control is c13 = ~A.
    """
    def blk_lp(): b.cx(PR, PL)
    def blk_c02():  # U = ~lp & s_t
        b.x(PL); b.rccx(PL, PT, U); b.x(PL)
    def blk_s02(): cswap(b, 0, 2, U)
    def blk_conv():  # U ^= f & ~lp -> U = p_t & ~lp (first control F)
        b.x(PL); b.rccx(F, PL, U); b.x(PL)
    def blk_c13():  # A = s_r & ~u  (control of swap(1,3) is ~A)
        b.x(U); b.rccx(PR, U, A); b.x(U)
    def blk_s13():
        b.x(A); cswap(b, 1, 3, A); b.x(A)
    def blk_par():
        b.cx(F, PT); b.cx(F, PR)
    return [blk_lp, blk_c02, blk_s02, blk_conv, blk_c13, blk_s13, blk_c13, blk_par]


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


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    U, A, W = b.alloc(3, "uaw")
    blocks = leg(b, U, A)
    for blk in blocks:
        blk()
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    b.rccx(q2(0), q2(1), A); b.rccx(q2(2), q2(3), W)
    qm = dict(r=PR, lp=PL, t=PT, u=U, w01=A, w23=W)
    terms = group_terms(beta, qm)
    order = [frozenset(qm[n] for n in S) for S in SUPPORT]
    walk_open(b, terms, order, F, frozenset([PR]))
    b.rccx(q2(2), q2(3), W); b.rccx(q2(0), q2(1), A)
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    # leg 2: first block is the parity block; its cx(F, PR) absorbs the open r toggle: cz(PR, F) then cx(F, PR)
    b.cx(F, PT)
    b.sdg(PR); b.cx(F, PR); b.s(PR); b.sdg(F)
    for blk in reversed(blocks[:-1]):
        blk()
    b.free([U, A, W])
    return b
