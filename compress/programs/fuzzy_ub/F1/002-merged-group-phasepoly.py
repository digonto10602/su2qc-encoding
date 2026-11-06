"""SUMMARY: parent r01-F1-001 frames, but the t=1 sectors 2,3,6,7 (one shared layout) get pair-AND ancillas w01,w23 and ONE merged phase polynomial on f over x=t~l, y=tl, r, w01, w23 (one-hot NOT split by r for t=1: 4 ancillas, 32 CX one-hot round trip); final frame re-factored to start with (1 2) so its CX cancels the last Bell-decoder CX; 172 CX.
DISCOVERY: sectors 2,3,6,7 are exactly the t=1 parity sectors and share one frame; on that frame their four C^k-R_x merge into one 12-term phase polynomial (16-CX closed walk) over x=t&~l, y=t&l, r, w01=fl0&fl1, w23=fl2&fl3, fitted exactly on the reachable domain (x,y exclusive), so the one-hot needs no r-split for t=1 (saves 16 CX).
DISCOVERY: in that merged polynomial the bare w01, w23 and constant Walsh terms of sectors 2,3,7,6 cancel exactly (angles 8b,-16b,8b,-4b), the merge is lossless.
DISCOVERY: the last frame (0 3)(1 3)(2 3) equals (1 2)(0 3)(1 3) (time order); starting it with cswap(2,1) cancels the final Bell-decoder CX(q2^r->q2^t) against the Fredkin's first CX (-2 CX).
"""
FAMILY = "F1"
PARENT = "r01-F1-001"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F = 1
PR, PT, PL = 3, 5, 7

PLAN = [('m', [(2, 3), (0, 1)]), (0, [(1, 2)], 1), ('m', [(0, 2)]), (1, [(0, 1)], -1), ('m', [(1, 3)]),
        (5, [(0, 1)], 1), ('m', [(0, 2)]),
        ('g', [(2, [(2, 3)], -1), (3, [(0, 1), (2, 3)], 1), (7, [(0, 1)], -1), (6, [], 1)]),
        (4, [(1, 2)], -1), ('m', [(2, 1), (0, 3), (1, 3)])]


def q2(i):
    return 2 * i


def cswap(b, i, j, skip_first=False):
    a, d = q2(i), q2(j)
    if not skip_first:
        b.cx(d, a)
    b.ccx(F, a, d); b.cx(d, a)


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
    anc = b.alloc(4, "onehot")
    hot = onehot(b, anc)
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
    onehot(b, anc, inverse=True)
    b.free(anc)
    for k in (PR, PT, PL): b.cx(F, k)
    return b
