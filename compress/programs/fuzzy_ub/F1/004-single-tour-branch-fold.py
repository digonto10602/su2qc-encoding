"""SUMMARY: one f-controlled frame tour id -> G=(3,0,1,2) -> id (6 Fredkins) for all 8 parity sectors: the first and last (0 2) swap is controlled by c = (p_r&~p_t) xor f&(p_t|p_r^p_l) (= f for t=1), which routes sectors 0,1,4,5 onto the sector-4 normal form at G, so one 3-control middle on ~p_t serves t=0 and the t=1 group polynomial is fitted directly on (p_t, p_r^p_l, p_r, w01, w23) without a one-hot; 116 CX, 12 qubits.
DISCOVERY: per-sector branch control of a frame swap (none / f=0 / f=1 / both) acts as a fold: with leg (0 2),(0 1),(2 3) the states (sector 0 none, 1 f=0 only, 4 f=1 only, 5 both) at the (0 2) swap put sectors 0,1,4,5 into the sector-4 normal form at G (decoder (1,2), value 2 with sign (-1)^(p_r^p_l)); no separate fold Fredkin, no sector-0 frame, one t=0 middle.
DISCOVERY: that control is one rccx toggle on a persistent u=p_r&~p_t line using e=~p_t&~(p_r^p_l); a Z on the line while it holds c multiplies the t=0 couplings by (-1)^(p_r^p_l) (t=1 by -1), making the four t=0 sectors identical.
DISCOVERY: with p_l'=p_r^p_l made by the parity frame itself (cx(q1^r,q1^l) first, still 3 CX) the t=1 group function needs no one-hot: its full Walsh expansion on (p_t, p_l', p_r, w01, w23) has 18 terms and a 20-CX closed walk (vs 8 CX one-hot + 2 CX l-restore + 16-CX walk); both group decoders cancel against the first two Fredkins of the closing leg.
"""
FAMILY = "F1"
PARENT = "r03-F3-003"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F = 1
PR, PT, PL = 3, 5, 7
GROUP = [(2, [(2, 3)], -1), (3, [(0, 1), (2, 3)], 1), (7, [(0, 1)], -1), (6, [], 1)]


def q2(i):
    return 2 * i


FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]


def cswap(b, i, j, skip_first=False, ctrl=F):
    a, d = q2(i), q2(j)
    if skip_first:
        b.ccx(ctrl, a, d); b.cx(d, a)
        return
    m = [ctrl, a, d]
    for g in FRED7:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def walk(nodes):
    """Closed shortest walk from empty set through all nodes (frozensets), Hamming metric (Held-Karp)."""
    nodes = list(nodes)
    n = len(nodes)
    if n == 0:
        return []
    d = lambda x, y: len(x ^ y)
    E = frozenset()
    INF = 10 ** 9
    dp = {}
    for i in range(n):
        dp[(1 << i, i)] = (d(E, nodes[i]), None)
    for mask in range(1, 1 << n):
        for i in range(n):
            if (mask, i) not in dp:
                continue
            c, _ = dp[(mask, i)]
            for j in range(n):
                if mask >> j & 1:
                    continue
                key = (mask | 1 << j, j)
                nc = c + d(nodes[i], nodes[j])
                if key not in dp or dp[key][0] > nc:
                    dp[key] = (nc, i)
    full = (1 << n) - 1
    best = min(range(n), key=lambda i: dp[(full, i)][0] + d(nodes[i], E))
    order = []
    mask, i = full, best
    while i is not None:
        order.append(nodes[i])
        _, pi = dp[(mask, i)]
        mask ^= 1 << i
        i = pi
    return order[::-1]


def phase_poly_rx(b, terms, t):
    """Apply prod_S exp(-i c_S/2 * X_t * chi_S) via H, CX walk, Rz, H. terms: {frozenset(qubits): angle}."""
    terms = {S: a for S, a in terms.items() if abs(a) > 1e-12}
    b.h(t)
    if frozenset() in terms:
        b.rz(terms[frozenset()], t)
    cur = frozenset()
    for S in walk([S for S in terms if S]) + [frozenset()]:
        for q in sorted(cur ^ S):
            b.cx(q, t)
        cur = S
        if S in terms and S:
            b.rz(terms[S], t)
    b.h(t)


SUPPORT = [['r', 'x'], ['w01', 'x'], ['r', 'y'], ['w01', 'y'], ['r', 'w23'], ['r', 'w01', 'x'], ['r', 'w23', 'x'],
           ['r', 'w01', 'y'], ['w01', 'w23', 'y'], ['r', 'w01', 'w23'], ['w01', 'w23', 'x', 'y'], ['r', 'w01', 'w23', 'x']]


def group_unsplit(secs, beta):
    """Exact fit of the t=1 group function on the reachable domain (x=t~l, y=tl exclusive) with SUPPORT."""
    th = {p: -4.0 * beta * s * 2 ** len(prs) for p, prs, s in secs}
    dom, G = [], []
    for xy in [(0, 0), (1, 0), (0, 1)]:
        for r in (0, 1):
            for a in (0, 1):
                for c in (0, 1):
                    d = dict(x=xy[0], y=xy[1], r=r, w01=a, w23=c)
                    x, y = xy
                    G.append(th[2] * x * (1 - r) * c + th[3] * x * r * a * c + th[6] * y * (1 - r) + th[7] * y * r * a)
                    dom.append(d)
    sup = [[]] + SUPPORT
    A = np.array([[(-1) ** sum(d[v] for v in S) for S in sup] for d in dom], float)
    c = np.linalg.lstsq(A, np.array(G), rcond=None)[0]
    assert np.abs(A @ c - G).max() < 1e-9
    return [(S, ci) for S, ci in zip(sup, c) if abs(ci) > 1e-12]


def add_and(terms, theta, cs):
    k = len(cs)
    for r in range(k + 1):
        for S in itertools.combinations(cs, r):
            key = frozenset(S)
            terms[key] = terms.get(key, 0.0) + theta * (-1) ** r / 2 ** k


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
def walkcost_np(nodes): return hk_order(nodes)[0]


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


def ctl_swap02(b, uline, e):
    """swap q2^0,q2^2 controlled by c = u xor f&~e (u = p_r&~p_t on uline, e = ~p_t&~p_l'), with Z on c."""
    b.x(e); b.rccx(F, e, uline); b.x(e)
    b.z(uline)
    cswap(b, 0, 2, ctrl=uline)
    b.x(e); b.rccx(F, e, uline); b.x(e)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    GSIGN = -1.0
    # parity frame with p_l' = p_r ^ p_l on wire 7
    b.cx(PR, PL); b.cx(F, PR); b.cx(F, PT)
    uline, e = b.alloc(2, "ue")
    b.x(PT); b.rccx(PR, PT, uline); b.x(PT)                  # u = p_r & ~p_t
    b.x(PT); b.x(PL); b.rccx(PT, PL, e); b.x(PT); b.x(PL)    # e = ~p_t & ~p_l'
    # leg 1: (0 2)[c], (0 1), (2 3)
    ctl_swap02(b, uline, e)
    cswap(b, 0, 1); cswap(b, 2, 3)
    # t=0 middle: decoder (1,2), R_x(-8 beta) on f controlled by ~p_t, w1, w2
    b.cx(q2(1), q2(2)); b.h(q2(1))
    b.x(PT)
    terms = {}
    add_and(terms, -8.0 * beta, [PT, q2(1), q2(2)])
    phase_poly_rx(b, terms, F)
    b.x(PT)
    b.h(q2(1)); b.cx(q2(1), q2(2))
    # group middle at G with decoders (0,1),(2,3); variables t=PT, l'=PL (=p_r^p_l), r=PR, w01, w23 (no one-hot)
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    w01, w23 = b.alloc(2, "w")
    b.rccx(q2(0), q2(1), w01); b.rccx(q2(2), q2(3), w23)
    th = {p: GSIGN * (-4.0 * beta * s * 2 ** len(prs)) for p, prs, s in GROUP}
    names = ['t', 'lp', 'r', 'w01', 'w23']
    qm = dict(t=PT, lp=PL, r=PR, w01=w01, w23=w23)
    subs = [S for k in range(6) for S in itertools.combinations(names, k)]
    pts = list(itertools.product(range(2), repeat=5))
    A = np.array([[(-1) ** sum(pt[names.index(v)] for v in S) for S in subs] for pt in pts], float)
    g = []
    for t, lp, r, a, c in pts:
        l = lp ^ r
        g.append(t * (th[2] * (1 - l) * (1 - r) * c + th[3] * (1 - l) * r * a * c + th[6] * l * (1 - r) + th[7] * l * r * a))
    coef = np.linalg.solve(A, np.array(g))
    terms = {}
    for S, ci in zip(subs, coef):
        if abs(ci) > 1e-12:
            terms[frozenset(qm[v] for v in S)] = ci
    phase_poly_rx_np(b, terms, F)
    b.rccx(q2(2), q2(3), w23); b.rccx(q2(0), q2(1), w01)
    b.free([w01, w23])
    # leg 2: (1 0) and (3 2) cancel the decoders' last CX, then (0 2)[c]
    b.h(q2(0)); cswap(b, 1, 0, skip_first=True)
    b.h(q2(2)); cswap(b, 3, 2, skip_first=True)
    ctl_swap02(b, uline, e)
    b.x(PT); b.x(PL); b.rccx(PT, PL, e); b.x(PT); b.x(PL)
    b.x(PT); b.rccx(PR, PT, uline); b.x(PT)
    b.free([uline, e])
    b.cx(F, PT); b.cx(F, PR); b.cx(PR, PL)
    return b
