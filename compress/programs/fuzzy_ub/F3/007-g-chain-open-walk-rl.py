"""SUMMARY: g chain + open walk at both parity CX: U: 0 -> ~s_r & ~p_t (controls swap(q2^1,q2^3)) -> g = ~p_t & (p_r ^ p_l) (rccx with ~s_l first), A = f & ~g (controls swap(q2^0,q2^2)), q1 basis (p_r, p_t, p_l) made by cx(f, p_t) before the lines and cx(f, p_r), cx(f, p_l) at the leg end, so the 9-rotation R_x polynomial on (r, t, l, g, w01, w23) runs as an open walk from the constant to {r, l} whose two closing toggles merge into the mirrored parity CX (12 CX instead of 13); the A toggle next to each Bell decode is fused with the w01 AND on A (tdg h . h t = I, -2 T each); 86 CX, T_fixed 80, 11 qubits.
DISCOVERY: exhaustive leg scenarios (all 36 three-CX parity schedules with each of q1^r, q1^t, q1^l targeted once, x placements of the rccx events, x the 1024 valid two-swap control pairs, both role assignments of the converted line U and the compute/uncompute line A) give 64 realisable (angle function, q1 basis, invariant u, absorbable ends) tuples; with U on the (0 2) swap u is always t & ~lp and the best open walk found is 13 CX (r06-F3-006, 87), with U on the (1 3) swap u = g and in basis (p_r, p_t, p_l) with ends {r, l} it is 12 CX (this program, 86).
DISCOVERY: relative-phase Fredkins do not fit the two-swap frame: with leg 2 the mirror of leg 1 the leg's relative phase, as a function of the input code, must be constant on each of the 41 non-trivial connected components of the target's sparsity graph (16 pairs, 24 quads, 1 octet; 120 codes are fixed points), and a Smith-form solve over Z_8 shows that 5-CX (Margolus core) and 6-CX (CS-residual core) Fredkins, and 8-CX RC3X doubly-controlled swaps replacing a control line, admit no correction by free single-wire phase gates at any monomial boundary or by same-time CZ gates.
"""
FAMILY = "F3"
PARENT = "r06-F3-006"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7
ORD = dict(b2=0, b4=1, b5=0)  # control order per rccx (b4: ~s_l first; the other order is not exact)


def q2(i):
    return 2 * i


FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]


def cswap(b, i, j, ctrl):
    a, d = q2(i), q2(j)
    m = [ctrl, a, d]
    for g in FRED7:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


# lambda(p_r, p_t, p_l) for (w01, w23) = (0,0), (0,1), (1,0), (1,1)
LAM = {(0, 0, 0): (0, -2, 0, 2), (0, 0, 1): (0, 2, 0, -2), (0, 1, 0): (0, 2, 0, -2), (0, 1, 1): (1, -1, -1, 1),
       (1, 0, 0): (0, 0, 2, -2), (1, 0, 1): (0, 0, -2, 2), (1, 1, 0): (0, 0, 0, 4), (1, 1, 1): (0, 0, 2, -2)}
# walk: const first, then these sets, open end {r, l}
ORDER = [['l'], ['l', 't', 'w23'], ['r', 'l', 't', 'w23'], ['r', 'l', 't', 'w01', 'w23'], ['r', 'l', 't', 'w01'],
         ['r', 't', 'g', 'w01'], ['r', 'g'], ['r', 'l', 'g']]


def group_terms(beta, qm):
    sup = [[]] + ORDER
    rows, th = [], []
    for r, t, l, x, y in itertools.product(range(2), repeat=5):
        g = (1 - t) & (r ^ l)
        v = dict(r=r, t=t, l=l, g=g, w01=x, w23=y)
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        th.append(-4.0 * beta * LAM[(r, t, l)][2 * x + y])
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9, np.abs(A @ c - th).max()
    return {frozenset(qm[n] for n in S): ci for S, ci in zip(sup, c) if abs(ci) > 1e-12}


def rc(b, a, c, t, o):
    if o: b.rccx(c, a, t)
    else: b.rccx(a, c, t)


def leg(b, U, A):
    def b1(): b.cx(F, PT)
    def b2():  # U ^= ~s_r & ~p_t
        b.x(PR); b.x(PT); rc(b, PR, PT, U, ORD['b2']); b.x(PR); b.x(PT)
    def b3(): cswap(b, 1, 3, U)
    def b4():  # U ^= ~p_t & ~s_l  -> U = g = ~p_t & (p_r ^ p_l)
        b.x(PT); b.x(PL); rc(b, PT, PL, U, ORD['b4']); b.x(PT); b.x(PL)
    def b5():  # A ^= f & ~g
        b.x(U); rc(b, F, U, A, ORD['b5']); b.x(U)
    def b6(): cswap(b, 0, 2, A)
    def b8(): b.cx(F, PR); b.cx(F, PL)
    return [b1, b2, b3, b4, b5, b6, b5, b8]


def rccx_head(b, a, c, t):
    """rccx(a, c, t) without its trailing tdg(t) h(t)."""
    b.h(t); b.t(t); b.cx(c, t); b.tdg(t); b.cx(a, t); b.t(t); b.cx(c, t)


def rccx_tail(b, a, c, t):
    """rccx(a, c, t) without its leading h(t) t(t)."""
    b.cx(c, t); b.tdg(t); b.cx(a, t); b.t(t); b.cx(c, t); b.tdg(t); b.h(t)


def build(spec):
    b = Builder(spec)
    U, A, W = b.alloc(3, "uaw")
    blocks = leg(b, U, A)
    for blk in blocks[:-2]:
        blk()
    # second A toggle of leg 1 (A ^= f & ~g) fused with the w01 AND on A: tdg h . h t = I
    b.x(U); rccx_head(b, F, U, A); b.x(U)
    blocks[-1]()
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    rccx_tail(b, q2(0), q2(1), A); b.rccx(q2(2), q2(3), W)
    qm = dict(r=PR, t=PT, l=PL, g=U, w01=A, w23=W)
    terms = group_terms(spec.beta, qm)
    b.h(F)
    b.rz(terms[frozenset()], F)
    cur = frozenset()
    for S in ORDER:
        S = frozenset(qm[n] for n in S)
        for q in sorted(cur ^ S): b.cx(q, F)
        cur = S; b.rz(terms[S], F)
    end = frozenset([PR, PL])
    for q in sorted(cur ^ end): b.cx(q, F)
    b.h(F)
    b.rccx(q2(2), q2(3), W); rccx_head(b, q2(0), q2(1), A)
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    # open end {r, l}: cz(k, F) then the mirrored parity cx(F, k) == sdg(k) cx(F, k) s(k) sdg(F)
    for k in (PL, PR):
        b.sdg(k); b.cx(F, k); b.s(k); b.sdg(F)
    b.x(U); rccx_tail(b, F, U, A); b.x(U)
    for blk in reversed(blocks[:-2]):
        blk()
    b.free([U, A, W])
    return b
