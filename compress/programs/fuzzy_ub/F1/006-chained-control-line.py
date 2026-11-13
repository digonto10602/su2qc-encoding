"""SUMMARY: r05-F1/F3 two-swap single-middle frame ((1 3)[c2], (0 2)[c1], Bell pairs (0,1),(2,3), one 9-term R_x phase polynomial on f, 14-CX walk) with the c2 control line and the persistent g line merged into ONE ancilla chain L: 0 -> c2 = ~p_t&~s_r -> g = ~p_t&(s_r^s_l) (the second rccx adds ~p_t&~s_l), so g costs no compute/uncompute of its own; the two rccx on the c1/w01 ancilla are fused (-2 T each side); 88 CX, 11 qubits.
DISCOVERY: (~p_t&~s_r) xor (~p_t&~s_l) = ~p_t&(p_r^p_l) = g, so one rccx turns the (1 3)-swap control into the persistent g line (L: 0 -> c2 -> g per leg, 4 rccx per leg instead of 5): 94 -> 88 CX, one ancilla fewer; with first control ~s_l on that rccx the left-leg relative phase is i^g (f-independent, it commutes with the R_x middle and cancels against the mirrored leg), so plain 3-CX rccx suffice.
DISCOVERY: exhaustive checks for the (0 2)(1 3) word: no other pair of transpositions or Bell pairing works and no single f-controlled swap gives Hermitian commuting sector maps; over all 1024 sector-option choices the only f-independent lines one rccx away from a control are g and t&~(p_r^p_l) (up to negation), and the latter needs a 14-term / 20-CX walk, so 4 rccx + 2 Fredkins per leg (29 CX with the 3 parity CX) is the floor of this family.
DISCOVERY: middle alternatives all tie at 20 CX for one singlet AND (line 6 + walk share): toggling w23 straight into the R_x target by rccx leaves (-1)^(c0*dS) (best walk 18 + 2 CZ), expanding w23 or w01 into its decoded wires needs 12 terms / walk 20, folding g into the w23 line needs 24 terms; none beats AND line + 14-CX walk.
"""
FAMILY = "F1"
PARENT = "r05-F1-005"
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


def hk_order(nodes):
    """closed walk from empty set through all nodes (Hamming metric), exact Held-Karp, numpy rows."""
    nodes=[frozenset(s) for s in nodes if s]
    n=len(nodes)
    if n==0: return 0,[]
    D=np.array([[len(a^b) for b in nodes] for a in nodes],np.int32)
    st=np.array([len(a) for a in nodes],np.int32)
    INF=10**6
    N=1<<n
    dp=np.full((N,n),INF,np.int32); par=np.full((N,n),-1,np.int8)
    for i in range(n): dp[1<<i,i]=st[i]
    for m in range(1,N):
        row=dp[m]
        if row.min()>=INF: continue
        tot=row[:,None]+D
        arg=tot.argmin(axis=0); best=tot[arg,np.arange(n)]
        for j in range(n):
            if not (m>>j)&1:
                mm=m|(1<<j)
                if best[j]<dp[mm,j]: dp[mm,j]=best[j]; par[mm,j]=arg[j]
    full=N-1
    fin=dp[full]+st; j=int(fin.argmin()); cost=int(fin[j])
    order=[]; m=full
    while j>=0:
        order.append(nodes[j]); pj=int(par[m,j]); m^=1<<j; j=pj
        if m==0: break
    return cost,order[::-1]
def phase_poly_rx_np(b, terms, t):
    """as phase_poly_rx, with the numpy Held-Karp walk order (exact)."""
    terms = {S: a for S, a in terms.items() if abs(a) > 1e-12}
    b.h(t)
    if frozenset() in terms:
        b.rz(terms[frozenset()], t)
    cur = frozenset()
    _, order = hk_order([S for S in terms if S])
    for S in order + [frozenset()]:
        for q in sorted(cur ^ S):
            b.cx(q, t)
        cur = S
        if S in terms and S:
            b.rz(terms[S], t)
    b.h(t)



# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}


SUPPORT = [['g'], ['r', 'g'], ['r', 't', 'w01', 'g'], ['lp', 't', 'w01'], ['lp', 't', 'w01', 'w23'], ['lp', 't', 'w23'],
           ['r', 'lp', 't', 'w23'], ['r', 'lp'], ['lp']]


def group_terms(beta, qm):
    """Exact fit of theta(p, w01, w23) = -4 beta lambda on the reachable domain (g = ~t & lp) with SUPPORT."""
    sup = [[]] + SUPPORT
    rows, th = [], []
    for idx in range(32):
        r, lp, t, x, y = [(idx >> k) & 1 for k in range(5)]
        v = dict(r=r, lp=lp, t=t, w01=x, w23=y, g=(1 - t) & lp)
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * (lp ^ r)]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9
    return {frozenset(qm[n] for n in S): ci for S, ci in zip(sup, c) if abs(ci) > 1e-12}


def nx(b, qs):
    for q in qs:
        b.x(q)


def rccx_pair(b, c0, c1, d0, d1, t):
    """rccx(c0, c1, t) followed by rccx(d0, d1, t), with the inner H.H and Tdg.T cancelled (-2 T)."""
    b.h(t); b.t(t)
    b.cx(c1, t); b.tdg(t); b.cx(c0, t); b.t(t); b.cx(c1, t)
    b.cx(d1, t); b.tdg(t); b.cx(d0, t); b.t(t); b.cx(d1, t)
    b.tdg(t); b.h(t)


def leg_head(b, L, a):
    """L: 0 -> c2 = ~p_t&~s_r, swap(q2^1,q2^3)[c2], L: c2 -> g = ~p_t&(s_r^s_l), a: 0 -> c1 = f&~g, swap(q2^0,q2^2)[c1]."""
    b.cx(F, PT)
    nx(b, [PT, PR]); b.rccx(PT, PR, L); nx(b, [PT, PR])
    cswap(b, 1, 3, L)
    nx(b, [PL, PT]); b.rccx(PL, PT, L); nx(b, [PL, PT])
    b.cx(PR, PL)
    b.x(L); b.rccx(F, L, a); b.x(L)
    cswap(b, 0, 2, a)


def leg_tail(b, L, a):
    """exact inverse of leg_head."""
    cswap(b, 0, 2, a)
    b.x(L); b.rccx(F, L, a); b.x(L)
    b.cx(PR, PL)
    nx(b, [PL, PT]); b.rccx(PL, PT, L); nx(b, [PL, PT])
    cswap(b, 1, 3, L)
    nx(b, [PT, PR]); b.rccx(PT, PR, L); nx(b, [PT, PR])
    b.cx(F, PT)


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
    w01 = a
    leg_head(b, g, a)
    b.cx(F, PR)
    decode(b)
    # a: c1 -> 0 -> w01 (two rccx on the same target, merged)
    b.x(g); rccx_pair(b, F, g, q2(0), q2(1), a); b.x(g)
    b.rccx(q2(2), q2(3), w23)
    terms = group_terms(beta, dict(r=PR, lp=PL, t=PT, w01=w01, w23=w23, g=g))
    phase_poly_rx_np(b, terms, F)
    b.rccx(q2(2), q2(3), w23)
    b.x(g); rccx_pair(b, q2(0), q2(1), F, g, a); b.x(g)
    encode(b)
    b.cx(F, PR)
    leg_tail(b, g, a)
    b.free([a, g, w23])
    return b
