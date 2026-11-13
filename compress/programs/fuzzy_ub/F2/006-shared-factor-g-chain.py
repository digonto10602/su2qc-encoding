"""SUMMARY: r05-F3-005 two-swap single-middle datapath with a shared-factor toggle chain on one line G: G = c2 = ~p_t & ~z_r (rccx) controls swap(q2^1,q2^3), then ONE rccx with the raw ~z_l wire turns it into the persistent g = ~p_t & (z_r^z_l) (c2 ^ ~p_t&~z_l = g) used by the c1 = f&~g swap(q2^0,q2^2) and the 9-term middle polynomial; mirrored on the way back; the separate g line and its 2 rccx disappear (-6 CX), and the c1-uncompute/w01-compute rccx pairs on one target are fused (Tdg H H T = I, -4 T); 88 CX, 11 qubits.
DISCOVERY: two AND toggles of one line with a shared factor A, rccx(A,C) then rccx(B^C, A) with the B^C control first, leave the line at A&B with only the invariant phase i^(A&B) (the (1,0,1) sign of rccx never fires because the line is 1 only when A=1); the mirrored leg gives (-i)^(A&B), so the pair is exact; with A=~p_t, C=~z_r, B=z_r^z_l the per-leg c2 control becomes the persistent g line for 3 CX instead of 3+6 (94 -> 88 CX).
DISCOVERY: exhaustive search over swap words reaching the common (01)(23) frame with controls b*f ^ k(p) (k any invariant function, i.e. any persistent lines): none with <=3 swaps when every f-coefficient b is constant, none with 3 swaps when only one b(p) is free; for the 2-swap word none of the 1024 valid control pairs has c1, c2 and c1^c2 all of the form AND+affine (also with g as a variable), so 4 rccx per leg is minimal for single-AND toggles.
DISCOVERY: consecutive rccx on one target fuse (head of the first + tail of the second: Tdg H H T = I, -2 T each); if they also share the twice-used second control y, the two middle CX(y->t) cancel too (4 CX for two toggles); an extra persistent line h = ~g & p_r obtained for free from the c1 chain does not shorten the middle walk (best 16 CX vs 14).
"""
FAMILY = "F2"
PARENT = "r05-F2-005"
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
    for r, lp, t, x, y in itertools.product(range(2), repeat=5):
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
    """G ^= ~z_l & ~p_t (PL holds raw z_l); first control ~z_l, so the -1 pattern (1,0,1) of rccx never fires."""
    nx(b, [PL, PT]); b.rccx(PL, PT, G); nx(b, [PL, PT])


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    a, G, w23 = b.alloc(3, "agw")
    b.cx(F, PT)                                  # PT = p_t
    r1(b, G)                                     # G = c2 = ~p_t & ~z_r
    cswap(b, 1, 3, G)
    r2(b, G)                                     # G = c2 ^ (~p_t & ~z_l) = ~p_t & (z_r ^ z_l) = g
    b.cx(PR, PL)                                 # PL = p_r ^ p_l
    # c1 = f & ~g on a, Fredkin (0 2), uncompute fused with the w01 AND of the middle
    b.x(G); b.rccx(F, G, a); b.x(G)
    cswap(b, 0, 2, a)
    b.x(G); rccx_head(b, F, G, a); b.x(G)
    b.cx(F, PR)                                  # PR = p_r
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    rccx_tail(b, q2(0), q2(1), a)                # a = w01
    b.rccx(q2(2), q2(3), w23)
    terms = group_terms(beta, dict(r=PR, lp=PL, t=PT, w01=a, w23=w23, g=G))
    phase_poly_rx_np(b, terms, F)
    b.rccx(q2(2), q2(3), w23)
    rccx_head(b, q2(0), q2(1), a)
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    b.cx(F, PR)
    b.x(G); rccx_tail(b, F, G, a); b.x(G)       # a = c1 (new f)
    cswap(b, 0, 2, a)
    b.x(G); b.rccx(F, G, a); b.x(G)
    b.cx(PR, PL)                                 # PL = raw z_l
    r2(b, G)                                     # G = c2 (new f)
    cswap(b, 1, 3, G)
    r1(b, G)                                     # G = 0
    b.cx(F, PT)
    b.free([a, G, w23])
    return b
