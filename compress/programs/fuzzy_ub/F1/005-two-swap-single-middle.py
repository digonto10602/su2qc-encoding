"""SUMMARY: two commuting branch-controlled swaps per leg, (1 3) on c2 = f&~t and (0 2) on c1 = (~t&~r) xor f xor c2&p_l', put all 8 parity sectors into ONE Bell-diagonal frame (pairs (0,1),(2,3)); a single middle (w01, w23 ANDs, 11-term phase polynomial on (t, r, p_l', w01, w23, u=~t&~r), 14-CX walk) serves t=0 and t=1; 4 Fredkins instead of 6, 98 CX, 11 rotations, 12 qubits.
DISCOVERY: an exhaustive search over per-sector branch states (none / f=0 / f=1 / both) shows that two commuting swaps (0 2),(1 3) with arbitrary controls bring every sector to a common pairing (0,1),(2,3), the t=0 sectors in the relaxed form 2 w01 (-1)^w23 that the shared w-lines handle for free, so t=0 and t=1 need one middle; in every such 2-swap solution both controls are nonlinear; with GF(2)-linear controls only, no leg of <= 4 swaps reaches the two-middle normal forms of r04-F1-004.
DISCOVERY: the c1 line shares the c2 AND: u holds ~t&~r for the whole circuit and is toggled per leg by cx(f,u) + rccx(c2, p_l', u) (4 CX), c2 = rccx(f, ~t) is computed and uncomputed in each leg (3+3 CX); total control cost 34 CX and no e-line.
DISCOVERY: using the persistent u = ~t&~r line as an extra phase-polynomial variable, the merged angle function has an exact 11-term Walsh fit (MILP over supports on (t, r, p_l', w01, w23, u)) with a 14-CX closed walk, versus 17 terms / 18 CX without u and 26 rotations in the parent.
"""
FAMILY = "F1"
PARENT = "r04-F1-004"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder
from su2plaq.compress import oracle

F = 1
PR, PT, PL = 3, 5, 7
FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]


def q2(i):
    return 2 * i


def cswap(b, ctrl, i, j):
    m = [ctrl, q2(i), q2(j)]
    for g in FRED7:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def hk_order(nodes, start=frozenset(), end=frozenset()):
    nodes = [frozenset(s) for s in dict.fromkeys(map(frozenset, nodes)) if s != start and s != end]
    n = len(nodes)
    if n == 0:
        return []
    D = np.array([[len(a ^ b) for b in nodes] for a in nodes], np.int32)
    st = np.array([len(a ^ start) for a in nodes], np.int32)
    en = np.array([len(a ^ end) for a in nodes], np.int32)
    INF = 10 ** 6
    N = 1 << n
    dp = np.full((N, n), INF, np.int32)
    par = np.full((N, n), -1, np.int16)
    for i in range(n):
        dp[1 << i, i] = st[i]
    for m in range(1, N):
        row = dp[m]
        if row.min() >= INF:
            continue
        tot = row[:, None] + D
        arg = tot.argmin(axis=0)
        best = tot[arg, np.arange(n)]
        for j in range(n):
            if not (m >> j) & 1:
                mm = m | (1 << j)
                if best[j] < dp[mm, j]:
                    dp[mm, j] = best[j]
                    par[mm, j] = arg[j]
    j = int((dp[N - 1] + en).argmin())
    order = []
    m = N - 1
    while j >= 0:
        order.append(nodes[j])
        pj = int(par[m, j])
        m ^= 1 << j
        j = pj
        if m == 0:
            break
    return order[::-1]


def sector_lambda(spec):
    """Exact diagonal values of the frame-and-decoder-conjugated sector blocks, from the oracle."""
    import dataclasses
    h = 1e-5
    Vp = np.asarray(oracle.target(dataclasses.replace(spec, beta=h)))
    Vm = np.asarray(oracle.target(dataclasses.replace(spec, beta=-h)))
    box = np.round(((Vp - Vm) / (4j * h)).real * 8) / 8
    def cxc(c, t, x):
        return x ^ (((x >> c) & 1) << t)
    perm = np.array([cxc(F, PT, cxc(F, PR, cxc(PR, PL, x))) for x in range(256)])
    P = np.zeros((256, 256))
    P[perm, np.arange(256)] = 1
    B = P @ box @ P.T
    idx = np.arange(256)
    bit = lambda q: (idx >> q) & 1
    q2i = lambda x: sum(((x >> (2 * i)) & 1) << i for i in range(4))
    def pmat(i, j):
        M = np.zeros((16, 16))
        for x in range(16):
            bi, bj = (x >> i) & 1, (x >> j) & 1
            y = x & ~(1 << i) & ~(1 << j) | (bi << j) | (bj << i)
            M[y, x] = 1
        return M
    def cxm(c, t):
        M = np.zeros((16, 16))
        for x in range(16):
            M[x ^ (((x >> c) & 1) << t), x] = 1
        return M
    def h1(i):
        Hd = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
        M = np.array([[1.0]])
        for k in reversed(range(4)):
            M = np.kron(M, Hd if k == i else np.eye(2))
        return M
    Dec = h1(2) @ cxm(2, 3) @ h1(0) @ cxm(0, 1)
    lam = {}
    for r, t, lp in itertools.product((0, 1), repeat=3):
        msk = (bit(PR) == r) & (bit(PT) == t) & (bit(PL) == lp)
        r1 = idx[msk & (bit(F) == 1)]; r0 = idx[msk & (bit(F) == 0)]
        r1 = r1[np.argsort([q2i(x) for x in r1])]; r0 = r0[np.argsort([q2i(x) for x in r0])]
        A = B[np.ix_(r1, r0)]
        L2 = lambda f: f & (1 - t)
        c1 = lambda f: ((1 - t) & (1 - r)) ^ f ^ (L2(f) & lp)
        G = [np.eye(16), np.eye(16)]
        for f in (0, 1):
            if L2(f): G[f] = pmat(1, 3) @ G[f]
            if c1(f): G[f] = pmat(0, 2) @ G[f]
        K = G[1] @ A @ G[0].T
        M = Dec @ K @ Dec.T
        assert np.abs(M - np.diag(np.diag(M))).max() < 1e-9 and np.abs(K - K.T).max() < 1e-9
        lam[(t, r, lp)] = np.diag(M)
    return lam


SUPPORT = [(), ('lp',), ('lp', 'r', 't', 'u'), ('lp', 'r', 't', 'u', 'w23'), ('lp', 't', 'w01'),
           ('lp', 't', 'w01', 'w23'), ('lp', 't', 'w23'), ('lp', 'w01'), ('r', 't', 'u'), ('r', 't', 'u', 'w01'), ('r', 'u', 'w01')]


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    lam = sector_lambda(spec)
    # merged angle function on (t, r, lp, w01, w23, u) with u = ~t&~r (the c1 line between the legs): fixed sparse
    # support, coefficients solved exactly from the oracle values (all 32 reachable points)
    u, L2, w01, w23 = b.alloc(4, "u L2 w01 w23")
    names = ['t', 'r', 'lp', 'w01', 'w23', 'u']
    rows, ys = [], []
    for (t, r, lp), lv in lam.items():
        for x in range(16):
            d = [(x >> i) & 1 for i in range(4)]
            rows.append(dict(t=t, r=r, lp=lp, w01=d[0] & d[1], w23=d[2] & d[3], u=(1 - t) & (1 - r)))
            ys.append(-4.0 * beta * lv[x])
    A = np.array([[(-1) ** sum(rw[v] for v in S) for S in SUPPORT] for rw in rows], float)
    coef, *_ = np.linalg.lstsq(A, np.array(ys), rcond=None)
    assert np.abs(A @ coef - np.array(ys)).max() < 1e-9
    qm = dict(t=PT, r=PR, lp=PL, w01=w01, w23=w23, u=u)
    terms = {frozenset(qm[v] for v in S): c for S, c in zip(SUPPORT, coef) if abs(c) > 1e-12}

    def leg():
        b.x(PT); b.rccx(F, PT, L2); b.x(PT)          # L2 = f & ~t
        cswap(b, L2, 1, 3)
        b.cx(F, u); b.rccx(L2, PL, u)                # u = ~t~r ^ f ^ (f~t) lp
        cswap(b, u, 0, 2)
        b.rccx(L2, PL, u); b.cx(F, u)
        b.x(PT); b.rccx(F, PT, L2); b.x(PT)

    b.cx(PR, PL); b.cx(F, PR); b.cx(F, PT)
    b.x(PT); b.x(PR); b.rccx(PT, PR, u); b.x(PT); b.x(PR)    # u = ~t & ~r
    leg()
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    b.rccx(q2(0), q2(1), w01); b.rccx(q2(2), q2(3), w23)
    b.h(F)
    if frozenset() in terms:
        b.rz(terms[frozenset()], F)
    cur = frozenset()
    for S in hk_order([S for S in terms if S]) + [frozenset()]:
        for q in sorted(cur ^ S):
            b.cx(q, F)
        cur = S
        if S:
            b.rz(terms[S], F)
    b.h(F)
    b.rccx(q2(2), q2(3), w23); b.rccx(q2(0), q2(1), w01)
    for (i, j) in [(0, 1), (2, 3)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    leg()
    b.x(PT); b.x(PR); b.rccx(PT, PR, u); b.x(PT); b.x(PR)
    b.free([u, L2, w01, w23])
    b.cx(F, PT); b.cx(F, PR); b.cx(PR, PL)
    return b
