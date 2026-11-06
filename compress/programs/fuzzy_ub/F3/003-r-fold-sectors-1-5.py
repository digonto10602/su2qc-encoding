"""SUMMARY: r02-F1-002 layout, but a (p_r & ~p_t & ~f)-controlled [Z q2^0 Z q2^1, then Fredkin(q2^0,q2^2)] at start/end maps sectors 1,5 exactly onto 0,4, so r drops out of the t=0 sectors: 6 frame Fredkins (7-CX), no r-split one-hot, 4 middles instead of 6; 151 CX.
DISCOVERY: sectors 1 and 5 are exactly equivalent to 0 and 4 (c=+1) under V=(V0,V1) on q2 with V1=I and V0=SWAP(0,2) Z0 Z1 (Z first) (or V0 = a 3-cycle on wires 0,1,2, no Paulis); no f-uniform signed permutation does it (64 joint solutions, all f-dependent); sectors 3/2 and 7/6 differ in rank (1 vs 4, 4 vs 16) so no r-merge exists there.
DISCOVERY: with 1,5 folded the frame sequence (2 3)(0 1) | (0 2)(1 3)(0 2)=(1 3) | back needs 6 Fredkins instead of 8.
"""
FAMILY = "F3"
PARENT = "r02-F1-002"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F = 1
PR, PT, PL = 3, 5, 7

PLAN = [('m', [(2, 3), (0, 1)]), (0, [(1, 2)], 1), ('m', [(1, 3)]),
        ('g', [(2, [(2, 3)], -1), (3, [(0, 1), (2, 3)], 1), (7, [(0, 1)], -1), (6, [], 1)]),
        (4, [(1, 2)], -1), ('m', [(2, 1), (0, 3), (1, 3)])]


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


def vmap(b, u, inverse=False):
    """V = (u & ~f)-controlled [Z q2^0 Z q2^1 then swap q2^0,q2^2]; maps sectors 1,5 exactly onto 0,4."""
    v = b.alloc(1, "v")[0]
    b.x(F); b.rccx(u, F, v); b.x(F)
    if not inverse:
        b.cz(v, q2(0)); b.cz(v, q2(1)); cswap(b, 0, 2, ctrl=v)
    else:
        cswap(b, 0, 2, ctrl=v); b.cz(v, q2(0)); b.cz(v, q2(1))
    b.x(F); b.rccx(u, F, v); b.x(F)
    b.free([v])


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


def onehot(b, anc, inverse=False, nosplit=(6, 2)):
    a11, a00 = anc[0], anc[1]
    ops = [('rccx', PT, PL, a11), ('cx', a11, PT), ('cx', a11, PL),
           ('cx', PT, a00), ('cx', PL, a00), ('cx', a11, a00), ('x', a00)]
    where = {}
    k = 0
    for q, tl in [(a11, 6), (PT, 2), (PL, 4), (a00, 0)]:
        if tl in nosplit:
            where[('u', tl)] = q
            continue
        b1 = anc[2 + k]; k += 1
        ops += [('rccx', q, PR, b1), ('cx', b1, q)]
        where[tl + 1], where[tl] = b1, q
    if inverse:
        ops = ops[::-1]
    for o in ops:
        getattr(b, o[0])(*o[1:])
    return where


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    for k in (PR, PT, PL): b.cx(F, k)
    u = b.alloc(1, "u")[0]
    b.x(PT); b.rccx(PR, PT, u); b.x(PT)
    vmap(b, u)
    anc = b.alloc(2, "onehot")
    hot = onehot(b, anc, nosplit=(6, 2, 4, 0))
    hot[0], hot[4] = hot[('u', 0)], hot[('u', 4)]
    dec = []

    def undo(pr):
        i, j = pr
        b.h(q2(i)); b.cx(q2(i), q2(j)); dec.remove(pr)

    def ensure(pairs):
        need = set(x for pr in pairs for x in pr)
        for pr in list(dec):
            if pr not in pairs and (pr[0] in need or pr[1] in need): undo(pr)
        for pr in pairs:
            if pr not in dec:
                i, j = pr; b.cx(q2(i), q2(j)); b.h(q2(i)); dec.append(pr)

    for step in PLAN:
        if step[0] == 'm':
            sw = step[1]
            skip = (sw[0][1], sw[0][0]) in dec        # decoder (i,j) ends with CX(q_i->q_j) = first CX of cswap(j,i)
            for pr in list(dec):
                if skip and pr == (sw[0][1], sw[0][0]):
                    b.h(q2(pr[0])); dec.remove(pr)
                else:
                    undo(pr)
            for k, (i, j) in enumerate(sw): cswap(b, i, j, skip_first=(skip and k == 0))
            continue
        if step[0] == 'g':
            secs = step[1]
            allp = sorted(set(pr for _, prs, _ in secs for pr in prs))
            ensure(allp)
            wq = {}
            useand = list(allp)
            for pr in useand:
                w = b.alloc(1)[0]
                b.rccx(q2(pr[0]), q2(pr[1]), w)
                wq[pr] = w
            qm = dict(x=hot[('u', 2)], y=hot[('u', 6)], r=PR, w01=wq[(0, 1)], w23=wq[(2, 3)])
            terms = {}
            for S, ci in group_unsplit(secs, beta):
                key = frozenset(qm[v] for v in S)
                terms[key] = terms.get(key, 0.0) + ci
            phase_poly_rx(b, terms, F)
            for pr in useand[::-1]:
                b.rccx(q2(pr[0]), q2(pr[1]), wq[pr])
                b.free([wq[pr]])
            continue
        p, pairs, s = step
        ensure(pairs)
        theta = -4.0 * beta * s * 2 ** len(pairs)
        flags = [q2(x) for pr in pairs for x in pr]
        terms = {}
        add_and(terms, theta, [hot[p]] + flags)
        phase_poly_rx(b, terms, F)
    for pr in list(dec): undo(pr)
    onehot(b, anc, inverse=True, nosplit=(6, 2, 4, 0))
    b.free(anc)
    vmap(b, u, inverse=True)
    b.x(PT); b.rccx(PR, PT, u); b.x(PT)
    b.free([u])
    for k in (PR, PT, PL): b.cx(F, k)
    return b
