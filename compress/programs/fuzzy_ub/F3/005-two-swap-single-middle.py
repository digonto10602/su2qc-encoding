"""SUMMARY: two-swap frame for all 8 parity sectors at once: swap(q2^1,q2^3) controlled by c2 = ~p_t & ~s_r and swap(q2^0,q2^2) controlled by c1 = f & ~g (g = ~p_t & (p_r^p_l), one persistent AND line) bring every sector to a diagonal form under the single Bell pairing (0,1),(2,3), so ONE R_x phase polynomial on f over (p_r, p_r^p_l, p_t, w01, w23, g) (9 terms, 14-CX walk) replaces both middles; 4 Fredkins instead of 6, 94 CX, 12 qubits.
DISCOVERY: with per-sector branch patterns c(p,f) on each swap, the 2-swap word (1 3)[c2](0 2)[c1] puts all 8 sectors (incl. p3 -> 4 w01 w23 and p6 -> (1-2w01)(1-2w23)) into diagonal form at the common decoder (0,1),(2,3); exhaustive search finds no such apex with <=4 swaps whose controls are affine in (f,p_r,p_t,p_l), nor with 3 swaps when only one control is an AND, so nonlinear controls are essential.
DISCOVERY: for that word the f-coefficient b(p) of one of the two controls is always nonlinear (forced by sectors 0,1,2,4,5,7), so 30 CX of control (one persistent AND line g + an rccx compute/uncompute pair per Fredkin use) is minimal for single-rccx lines; routing costs 4*7+30 = 58 CX against 64 in r04-F1-004, with one middle instead of two.
DISCOVERY: using the persistent g line as a polynomial variable cuts the merged middle from 15 to 9 Walsh terms (walk 16 -> 14 CX); an IDA* over general CX parity networks (all wires as targets) proves 14 optimal for every MILP support with <= 12 terms.
"""
FAMILY = "F3"
PARENT = "r04-F3-004"
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


def c2_swap(b, a):
    """swap q2^1,q2^3 controlled by c2 = ~p_t & ~s_r (T holds p_t, R holds raw s_r)."""
    nx(b, [PT, PR]); b.rccx(PT, PR, a); nx(b, [PT, PR])
    cswap(b, 1, 3, a)
    nx(b, [PT, PR]); b.rccx(PT, PR, a); nx(b, [PT, PR])


def c1_swap(b, a, g):
    """swap q2^0,q2^2 controlled by c1 = f & ~g, g = ~p_t & (p_r^p_l)."""
    b.x(g); b.rccx(F, g, a); b.x(g)
    cswap(b, 0, 2, a)
    b.x(g); b.rccx(F, g, a); b.x(g)


def g_line(b, g):
    b.x(PT); b.rccx(PT, PL, g); b.x(PT)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    a, a2, g, w23 = b.alloc(4, "aagw")
    b.cx(F, PT); b.cx(PR, PL)
    g_line(b, g)
    c2_swap(b, a2)
    c1_swap(b, a, g)
    b.cx(F, PR)
    # middle: decoders (0,1),(2,3), singlet ANDs, one R_x phase polynomial on f for all 8 sectors
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    w01 = a
    b.rccx(q2(0), q2(1), w01); b.rccx(q2(2), q2(3), w23)
    terms = group_terms(beta, dict(r=PR, lp=PL, t=PT, w01=w01, w23=w23, g=g))
    phase_poly_rx_np(b, terms, F)
    b.rccx(q2(2), q2(3), w23); b.rccx(q2(0), q2(1), w01)
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    b.cx(F, PR)
    c1_swap(b, a, g)
    c2_swap(b, a2)
    g_line(b, g)
    b.cx(PR, PL); b.cx(F, PT)
    b.free([a, a2, g, w23])
    return b
