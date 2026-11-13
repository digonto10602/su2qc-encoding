"""SUMMARY: r07-F1-007 (same control chain, middle and 10-CX open walk) with both Fredkins and both Bell decoders of each leg replaced by one Pauli-scheduled q2 block: SWAP^c = 7 commuting pi/8 Pauli rotations {Z_c, XX, YY, ZZ, Z_c XX, Z_c YY, Z_c ZZ}; an 8-CX q2 Clifford skeleton (2 CX per Fredkin pair, 4 CX into the middle frame) makes each pair Pauli weight-1 somewhere, so the 6 c-free rotations are single T gates on a q2 wire and the 3 c-terms per Fredkin are a 4-CX pattern CX(Qa->line) CX(Qb->line) CX(Qa->line) CX(Qb->line) on the control line (L = c2, a = c1); 16 CX per leg as before but 7 T per Fredkin instead of 9: 84 CX, T_fixed 72 (was 80), T_eps 638, 11 qubits.
DISCOVERY: a Fredkin SWAP_ij^c is the product of 7 commuting pi/8 Pauli rotations (Z_c, Q, Z_c Q for Q in XX, YY, ZZ on (i,j)); inside a leg each Q rotation can sit at ANY point of a q2 Clifford skeleton where Q is weight-1 (one T, no CX) and the three Z_c Q rotations need only the line pattern CX(Qa->c) CX(Qb->c) CX(Qa->c) CX(Qb->c) (4 CX, line content c+Qa, c+Qc, c+Qb), so the Fredkin's own frame CX can be shared with the leg's path to the middle Bell frame; exact signs from Clifford tracking (qiskit Pauli.evolve), leg verified as K_B * SWAP02^a * SWAP13^L to 4e-16.
DISCOVERY: exhaustive BFS over 4-wire q2 Clifford skeletons (local Cliffords free, 54 CX cosets, exact frame-B distance table over 79800 B-states as A* bound): with line-target c-parts no skeleton <= 7 CX gives all 6 visibilities + both c-part patterns (13 before 02) + the middle frame (min 8, i.e. 16 per leg = tie with 2 FRED7 + 2 decoders); the CCZ-in-Bell-frame variant (dec, CCZ with its within-pair CX absorbed, recouple) needs >= 6 skeleton CX + 10; one FRED7 at a Fredkin-able point + one scheduled pair also gives 16.
DISCOVERY: negative: no q2 transposition product and not sqrt(SWAP13) sqrt(SWAP02) commutes with the plaquette (op-norm commutator 1 to 2), and no pair Pauli of (1,3) or (0,2) is diagonal in the middle frame (its diagonal group is G01 x G23), so the c-free sqrt(SWAP) half of the Fredkins can be neither dropped nor pushed through the middle.
"""
FAMILY = "F1"
PARENT = "r07-F1-007"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7

# q2 skeleton of one leg (wires 0..3 = q2 of links b, r, t, l; wire 4 = line L, wire 5 = line a), split at the line
# periods: SEG_A while L holds c2 = ~p_t&~s_r, SEG_B while a holds c1 = f&~g, SEG_C after (ends in the middle frame).
SEG_A = [('t', 4), ('cx', 0, 2), ('h', 0), ('t', 0), ('t', 2), ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 0), ('tdg', 0), ('cx', 1, 3), ('h', 1), ('t', 1), ('t', 3), ('cx', 1, 4), ('tdg', 4), ('cx', 3, 4), ('t', 4), ('cx', 1, 4), ('tdg', 4), ('cx', 3, 4), ('s', 0), ('h', 0), ('h', 2), ('s', 2), ('h', 2), ('h', 1)]
SEG_B = [('t', 5), ('h', 2), ('cx', 2, 5), ('tdg', 5), ('h', 0), ('cx', 0, 5), ('tdg', 5), ('cx', 2, 5), ('t', 5), ('cx', 0, 5), ('h', 2), ('h', 0)]
SEG_C = [('h', 3), ('cx', 1, 3), ('h', 1), ('tdg', 1), ('z', 1), ('cx', 0, 1), ('s', 0), ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 2), ('s', 2), ('h', 2), ('h', 3), ('s', 3), ('cx', 2, 3), ('h', 1), ('h', 2), ('sdg', 2), ('h', 2), ('cx', 1, 2), ('s', 3), ('h', 3), ('sdg', 1), ('h', 1), ('h', 2)]
# middle frame: the singlet indicators of q2 pairs (0,1) and (2,3) are ANDs of these (wire, negated) literals
LITS = {'01': [(1, True), (0, True)], '23': [(3, False), (2, False)]}

# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
SUPPORT = [['t'], ['l', 't'], ['r', 't', 'v'], ['l', 'r', 't', 'v'], ['l', 'r', 't', 'w01'], ['r', 't', 'v', 'w01'],
           ['l', 't', 'w23'], ['l', 'r', 't', 'w23'], ['l', 'r', 't', 'w01', 'w23']]
OPEN = ['r', 't', 'l']
INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's', 'h': 'h', 'x': 'x', 'z': 'z', 'cx': 'cx'}


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
    if cz_after:
        b.sdg(k); b.cx(F, k); b.s(k); b.s(F)
    else:
        b.cx(F, k)


def cz_par(b, k, cz_before):
    if cz_before:
        b.sdg(k); b.cx(F, k); b.s(k); b.sdg(F)
    else:
        b.cx(F, k)


def emit(b, seg, wm, inverse=False):
    ops = [(INV[o[0]],) + tuple(o[1:]) for o in reversed(seg)] if inverse else seg
    for o in ops:
        getattr(b, o[0])(*[wm[q] for q in o[1:]])


def leg_head(b, L, a, X0, wm):
    cx_par(b, PT, PT in X0)
    nx(b, [PT, PR]); b.rccx(PT, PR, L); nx(b, [PT, PR])
    emit(b, SEG_A, wm)
    nx(b, [PL, PT]); b.rccx(PL, PT, L); nx(b, [PL, PT])
    cx_par(b, PL, PL in X0)
    b.x(L); b.rccx(F, L, a); b.x(L)
    emit(b, SEG_B, wm)
    cx_par(b, PR, PR in X0)
    emit(b, SEG_C, wm)


def leg_tail(b, L, a, X1, wm):
    emit(b, SEG_C, wm, True)
    cz_par(b, PR, PR in X1)
    emit(b, SEG_B, wm, True)
    b.x(L); b.rccx(F, L, a); b.x(L)
    cz_par(b, PL, PL in X1)
    nx(b, [PL, PT]); b.rccx(PL, PT, L); nx(b, [PL, PT])
    emit(b, SEG_A, wm, True)
    nx(b, [PT, PR]); b.rccx(PT, PR, L); nx(b, [PT, PR])
    cz_par(b, PT, PT in X1)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    a, g, w23 = b.alloc(3, "agw")
    wm = {0: 0, 1: 2, 2: 4, 3: 6, 4: g, 5: a}
    (u0, n0), (u1, n1) = LITS['01']
    (v0, m0), (v1, m1) = LITS['23']
    u0, u1, v0, v1 = wm[u0], wm[u1], wm[v0], wm[v1]
    neg01 = [q for q, n in ((u0, n0), (u1, n1)) if n]
    neg23 = [q for q, n in ((v0, m0), (v1, m1)) if n]
    qm = dict(r=PR, t=PT, l=PL, v=g, w01=a, w23=w23)
    terms = group_terms(beta)
    M = frozenset(OPEN)
    _, order = open_order([S for S in terms if S], M)
    X0 = frozenset(qm[n] for n in order[0] & M)
    X1 = frozenset(qm[n] for n in order[-1] & M)
    leg_head(b, g, a, X0, wm)
    nx(b, neg01); b.x(g); rccx_pair(b, F, g, u0, u1, a); b.x(g); nx(b, neg01)
    nx(b, neg23); b.rccx(v0, v1, w23); nx(b, neg23)
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
    nx(b, neg23); b.rccx(v0, v1, w23); nx(b, neg23)
    nx(b, neg01); b.x(g); rccx_pair(b, u0, u1, F, g, a); b.x(g); nx(b, neg01)
    leg_tail(b, g, a, X1, wm)
    b.free([a, g, w23])
    return b
