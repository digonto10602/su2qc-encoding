"""SUMMARY: r06-F1-006 control chain (L: 0 -> ~p_t&~s_r [(1 3) Fredkin] -> g = ~p_t&(p_r^p_l), a: f&~g [(0 2) Fredkin], a: c1 -> 0 -> w01 fused, w23 AND, 2 Fredkins + 4 rccx per leg) with cx(s_r, q1^l) replaced by cx(f, q1^l) so the middle sees p_l (not p_r^p_l) and all three leg parity CX(f -> q1^{r,t,l}) can carry walk-end toggles as free CZ(k, f) (a CZ(k, f) commutes with every leg gate that uses q1^k and f only as controls); the R_x phase polynomial on f (9 terms, no constant, over p_r, p_t, p_l, g, w01, w23) is an open walk with free ends in {p_r, p_t, p_l}: 10 CX instead of 14; 84 CX, 11 qubits.
DISCOVERY: a walk-end toggle CX(k -> f) next to H(f) equals CZ(k, f) on the leg side, and CZ(k, f) commutes with rccx/Fredkin/CX gates that use k and f only as controls (an X pair on k gives Z_f twice), so it can travel to ANY parity CX(f -> k) of the leg, not just the adjacent one, and merge there for free (cx then cz = sdg(k) cx s(k) s(f)); in the F1-006 leg with p_l on the q1^l wire all of {p_r, p_t, p_l} are free walk ends.
DISCOVERY: open-walk Held-Karp over exact Walsh supports (minimal size up to +2 terms per W/V component) for every 2-swap control pattern whose two lines cost 4 plain rccx per leg (only the u = t&~lp class of r06-F3 and the g = ~t&lp class of r06-F1 exist): g with p_l on the wire and free ends {r,t,l} gives 10 CX with 9 terms (the minimum term count; IDA* over general CX networks finds no 9-CX network for this support), u gives 11; with lp on the wire (free ends {r,t}) g gives 11-12 and u 13.
DISCOVERY: negative: no valid control pair has a control with constant f-coefficient (b13 xor b02 = t | lp in all 2048 pairs, so a single line cannot serve both Fredkins); the Fredkin tail CX plus the two Bell-decoder CX form a GL(4,2) block of CX distance 4 in all 16 orientations; toggling w23 straight into f by rccx ties at 16 CX (walk 8 + 6 + 2 CZ residual).
"""
FAMILY = "F1"
PARENT = "r06-F1-006"
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



# support (sets over r=p_r, t=p_t, l=p_l, v=g, w01, w23); no constant term
SUPPORT = [['t'], ['l', 't'], ['r', 't', 'v'], ['l', 'r', 't', 'v'], ['l', 'r', 't', 'w01'], ['r', 't', 'v', 'w01'],
           ['l', 't', 'w23'], ['l', 'r', 't', 'w23'], ['l', 'r', 't', 'w01', 'w23']]
OPEN = ['r', 't', 'l']   # walk end toggles of these wires merge into the parity CX(f -> wire) of the adjacent leg


def group_terms(beta):
    sup = [[]] + SUPPORT
    rows, th = [], []
    for r, t, l, x, y in itertools.product(range(2), repeat=5):
        v = dict(r=r, t=t, l=l, w01=x, w23=y, v=(1 - t) & (r ^ l))
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * l]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9, np.abs(A @ c - th).max()
    return {frozenset(S): ci for S, ci in zip(sup, c) if abs(ci) > 1e-12}


def open_order(nodes, M):
    """exact Held-Karp for the open walk: start and end toggles of wires in M are free."""
    nodes = [frozenset(s) for s in nodes]
    n = len(nodes)
    INF = 10 ** 6
    D = [[len(a ^ b) for b in nodes] for a in nodes]
    st = [len(a - M) for a in nodes]
    N = 1 << n
    dp = [[INF] * n for _ in range(N)]
    par = [[-1] * n for _ in range(N)]
    for i in range(n):
        dp[1 << i][i] = st[i]
    for m in range(1, N):
        for j in range(n):
            vj = dp[m][j]
            if vj >= INF or not (m >> j) & 1:
                continue
            for k in range(n):
                if (m >> k) & 1:
                    continue
                w = vj + D[j][k]
                if w < dp[m | 1 << k][k]:
                    dp[m | 1 << k][k] = w
                    par[m | 1 << k][k] = j
    best = min(range(n), key=lambda j: dp[N - 1][j] + st[j])
    cost = dp[N - 1][best] + st[best]
    order = []
    m, j = N - 1, best
    while j >= 0:
        order.append(nodes[j])
        pj = par[m][j]
        m ^= 1 << j
        j = pj
    return cost, order[::-1]


def nx(b, qs):
    for q in qs:
        b.x(q)


def rccx_pair(b, c0, c1, d0, d1, t):
    """rccx(c0, c1, t) followed by rccx(d0, d1, t), with the inner H.H and Tdg.T cancelled (-2 T)."""
    b.h(t); b.t(t)
    b.cx(c1, t); b.tdg(t); b.cx(c0, t); b.t(t); b.cx(c1, t)
    b.cx(d1, t); b.tdg(t); b.cx(d0, t); b.t(t); b.cx(d1, t)
    b.tdg(t); b.h(t)


def cx_par(b, k, cz_after):
    """parity CX(f -> k); if cz_after, followed by CZ(k, f) at no CX cost."""
    if cz_after:
        b.sdg(k); b.cx(F, k); b.s(k); b.s(F)
    else:
        b.cx(F, k)


def cz_par(b, k, cz_before):
    """parity CX(f -> k); if cz_before, preceded by CZ(k, f) at no CX cost."""
    if cz_before:
        b.sdg(k); b.cx(F, k); b.s(k); b.sdg(F)
    else:
        b.cx(F, k)


def leg_head(b, L, a, X0):
    """L: 0 -> c2 = ~p_t&~s_r, swap(q2^1,q2^3)[c2], L: c2 -> g = ~p_t&(s_r^s_l), a: 0 -> c1 = f&~g, swap(q2^0,q2^2)[c1].
    The parity CX's carry the CZ(k, f) of the walk's opening toggles (k in X0)."""
    cx_par(b, PT, PT in X0)
    nx(b, [PT, PR]); b.rccx(PT, PR, L); nx(b, [PT, PR])
    cswap(b, 1, 3, L)
    nx(b, [PL, PT]); b.rccx(PL, PT, L); nx(b, [PL, PT])
    cx_par(b, PL, PL in X0)
    b.x(L); b.rccx(F, L, a); b.x(L)
    cswap(b, 0, 2, a)
    cx_par(b, PR, PR in X0)


def leg_tail(b, L, a, X1):
    """exact inverse of leg_head (CZ(k, f) of the walk's closing toggles, k in X1, merged before the parity CX's)."""
    cz_par(b, PR, PR in X1)
    cswap(b, 0, 2, a)
    b.x(L); b.rccx(F, L, a); b.x(L)
    cz_par(b, PL, PL in X1)
    nx(b, [PL, PT]); b.rccx(PL, PT, L); nx(b, [PL, PT])
    cswap(b, 1, 3, L)
    nx(b, [PT, PR]); b.rccx(PT, PR, L); nx(b, [PT, PR])
    cz_par(b, PT, PT in X1)


def decode(b):
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))


def encode(b):
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    a, g, w23 = b.alloc(3, "agw")
    qm = dict(r=PR, t=PT, l=PL, v=g, w01=a, w23=w23)
    terms = group_terms(beta)
    M = frozenset(OPEN)
    _, order = open_order([S for S in terms if S], M)
    X0 = frozenset(qm[n] for n in order[0] & M)
    X1 = frozenset(qm[n] for n in order[-1] & M)
    leg_head(b, g, a, X0)
    decode(b)
    b.x(g); rccx_pair(b, F, g, q2(0), q2(1), a); b.x(g)
    b.rccx(q2(2), q2(3), w23)
    # R_x phase polynomial on f: open walk, the X0 / X1 toggles live in the legs as CZ(k, f)
    b.h(F)
    if frozenset() in terms:
        b.rz(terms[frozenset()], F)
    cur = X0
    for S in order:
        Sq = frozenset(qm[n] for n in S)
        for q in sorted(cur ^ Sq):
            b.cx(q, F)
        cur = Sq
        b.rz(terms[S], F)
    for q in sorted(cur ^ X1):
        b.cx(q, F)
    b.h(F)
    b.rccx(q2(2), q2(3), w23)
    b.x(g); rccx_pair(b, q2(0), q2(1), F, g, a); b.x(g)
    encode(b)
    leg_tail(b, g, a, X1)
    b.free([a, g, w23])
    return b
