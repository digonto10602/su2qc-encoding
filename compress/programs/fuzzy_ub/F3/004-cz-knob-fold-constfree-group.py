"""SUMMARY: r-fold of sectors 1,5 onto 0,4 with OR-merged first Fredkin, CZ(F,PR)/CZ(F,PL) sign knobs absorbed into the parity CX, t=1 group at the (0 2) frame fitted constant-free (11 terms, walk 14), one-AND selector lines (5 CX).
DISCOVERY: A CZ(F,k) next to a parity CX(F->k) costs no CX ([cx,cz] = sdg(k) cx s(k) s(F)); these free (-1)^r and (-1)^l sign knobs make the r-fold of sectors 1,5 CZ-free and let the t=1 group take an r-signed angle function.
DISCOVERY: The t=1 group (sectors 2,3,6,7) stays diagonal after Bell decoding of pairs (0,1),(2,3) at four common frames (2,1,0,3),(2,0,1,3),(3,1,0,2),(3,0,1,2); each admits a constant-free 11-term phase polynomial with walk 14 CX.
DISCOVERY: With a single AND ancilla a=t&l the one-hot sector lines are affine in (t,l,a); a DP over CX among PT,PL,a gives all line changes in 5 CX; fitting the group with only one singlet AND instead of two needs 23-27 terms (worse).
"""
FAMILY = "F3"
PARENT = "r03-F3-003"

import itertools
import numpy as np

F = 1
PR, PT, PL = 3, 5, 7


def q2(i):
    return 2 * i


FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]
INV = {'h': 'h', 's': 'sdg', 'sdg': 's', 't': 'tdg', 'tdg': 't', 'z': 'z', 'cx': 'cx', 'x': 'x'}
FRED7_DG = [(INV[g[0]],) + tuple(g[1:]) for g in FRED7[::-1]]
RCCX = [('h', 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('h', 2)]
RCCX_DG = [(INV[g[0]],) + tuple(g[1:]) for g in RCCX[::-1]]


class L:
    def __init__(self):
        self.g = []

    def add(self, name, *qs, p=None):
        self.g.append((name, tuple(qs), p))

    def seq(self, s, m):
        for g in s:
            self.add(g[0], *[m[k] for k in g[1:]])

    def rccx(self, a, b, t, dg=False):
        self.seq(RCCX_DG if dg else RCCX, [a, b, t])

    def fred(self, c, i, j, var=0):
        """Fredkin(c; i, j) on raw qubits; var: 0 FRED7(i,j), 1 FRED7(j,i), 2 DG(i,j), 3 DG(j,i)."""
        a, d = (i, j) if var in (0, 2) else (j, i)
        self.seq(FRED7 if var < 2 else FRED7_DG, [c, a, d])


# ------------------------------------------------------------------ peephole
_I2 = np.eye(2)
_M1 = {'h': np.array([[1, 1], [1, -1]]) / np.sqrt(2), 'x': np.array([[0, 1], [1, 0]]), 'z': np.diag([1, -1]),
       's': np.diag([1, 1j]), 'sdg': np.diag([1, -1j]), 't': np.diag([1, np.exp(1j * np.pi / 4)]),
       'tdg': np.diag([1, np.exp(-1j * np.pi / 4)])}
DIAG1 = {'z', 's', 'sdg', 't', 'tdg', 'rz'}
PH = {'t': 1, 's': 2, 'z': 4, 'sdg': 6, 'tdg': 7}
PHN = {1: ['t'], 2: ['s'], 3: ['s', 't'], 4: ['z'], 5: ['z', 't'], 6: ['sdg'], 7: ['tdg']}


def commutes(g1, g2):
    n1, q1, _ = g1
    n2, q2_, _ = g2
    s = set(q1) & set(q2_)
    if not s:
        return True
    # structural rules
    def role(g, q):
        n, qs, _ = g
        if n in DIAG1 or n == 'cz':
            return 'Z'
        if n == 'x':
            return 'X'
        if n == 'h':
            return 'H'
        if n == 'cx':
            return 'Z' if qs[0] == q else 'X'
        return '?'
    for q in s:
        r1, r2 = role(g1, q), role(g2, q)
        if '?' in (r1, r2) or 'H' in (r1, r2):
            if g1[0] == 'h' and g2[0] == 'h':
                continue
            return False
        if r1 != r2:
            return False
    return True


def inverse_pair(g1, g2):
    if g1[1] != g2[1]:
        return False
    a, b = g1[0], g2[0]
    if a in ('cx', 'h', 'x', 'z', 'cz') and a == b:
        return True
    if (a, b) in (('s', 'sdg'), ('sdg', 's'), ('t', 'tdg'), ('tdg', 't')):
        return True
    return False


def peephole(gs):
    gs = list(gs)
    changed = True
    while changed:
        changed = False
        out = []
        for g in gs:
            done = False
            for k in range(len(out) - 1, -1, -1):
                h = out[k]
                if inverse_pair(h, g):
                    del out[k]
                    done = True
                    changed = True
                    break
                # merge phase gates on same qubit
                if g[0] in PH and h[0] in PH and g[1] == h[1] and len(PHN.get((PH[g[0]] + PH[h[0]]) % 8, [])) < 2:
                    tot = (PH[g[0]] + PH[h[0]]) % 8
                    del out[k]
                    for nm in PHN.get(tot, []):
                        out.insert(k, (nm, g[1], None))
                    done = True
                    changed = True
                    break
                if not commutes(h, g):
                    break
            if not done:
                out.append(g)
        gs = out
    return gs


def cx_count(gs):
    return sum(1 for g in gs if g[0] in ('cx', 'cz'))


_WC = {}


def walk(nodes):
    key = tuple(sorted(tuple(sorted(n)) for n in nodes))
    if key in _WC:
        return list(_WC[key])
    r = _walk(nodes)
    _WC[key] = list(r)
    return r


def _walk(nodes):
    nodes = sorted(nodes, key=lambda n: sorted(n))
    n = len(nodes)
    if n == 0:
        return []
    d = lambda x, y: len(x ^ y)
    E = frozenset()
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


def phase_poly_rx(Lc, terms, t):
    terms = {S: a for S, a in terms.items() if abs(a) > 1e-12}
    Lc.add('h', t)
    if frozenset() in terms:
        Lc.add('rz', t, p=terms[frozenset()])
    cur = frozenset()
    for S in walk([S for S in terms if S]) + [frozenset()]:
        for q in sorted(cur ^ S):
            Lc.add('cx', q, t)
        cur = S
        if S in terms and S:
            Lc.add('rz', t, p=terms[S])
    Lc.add('h', t)


def add_and(terms, theta, cs):
    """cs: list of (qubit, polarity) with polarity 1 = control on |1>, 0 = control on |0>."""
    k = len(cs)
    for r in range(k + 1):
        for S in itertools.combinations(cs, r):
            key = frozenset(q for q, _ in S)
            sgn = (-1) ** sum(1 for _, pol in S if pol == 1)
            terms[key] = terms.get(key, 0.0) + theta * sgn / 2 ** k


SUPPORT = [['r', 'x'], ['w01', 'x'], ['r', 'y'], ['w01', 'y'], ['r', 'w23'], ['r', 'w01', 'x'], ['r', 'w23', 'x'],
           ['r', 'w01', 'y'], ['w01', 'w23', 'y'], ['r', 'w01', 'w23'], ['w01', 'w23', 'x', 'y'], ['r', 'w01', 'w23', 'x']]


def group_unsplit(secs, beta, support=SUPPORT, rsign=1):
    th = {p: -4.0 * beta * s * 2 ** len(prs) for p, prs, s in secs}
    dom, G = [], []
    for xy in [(0, 0), (1, 0), (0, 1)]:
        for r in (0, 1):
            for a in (0, 1):
                for c in (0, 1):
                    d = dict(x=xy[0], y=xy[1], r=r, w01=a, w23=c)
                    x, y = xy
                    G.append((th[2] * x * (1 - r) * c + th[3] * x * r * a * c + th[6] * y * (1 - r) + th[7] * y * r * a) * rsign ** r)
                    dom.append(d)
    sup = [[]] + support
    A = np.array([[(-1) ** sum(d[v] for v in S) for S in sup] for d in dom], float)
    c = np.linalg.lstsq(A, np.array(G), rcond=None)[0]
    assert np.abs(A @ c - G).max() < 1e-9
    return [(S, ci) for S, ci in zip(sup, c) if abs(ci) > 1e-12]


SUPPORT_RS = [['x'], ['y'], ['w23'], ['x', 'w01'], ['x', 'w23'], ['y', 'w01'], ['w01', 'w23'], ['x', 'r', 'w01'],
              ['x', 'w01', 'w23'], ['y', 'r', 'w01'], ['r', 'w01', 'w23'], ['x', 'r', 'w01', 'w23']]

from collections import deque

GROUP = [(2, [(2, 3)], -1), (3, [(0, 1), (2, 3)], 1), (7, [(0, 1)], -1), (6, [], 1)]
SUPPORT_RY = [['w01'], ['w23'], ['x', 'y'], ['x', 'w23'], ['r', 'w01'], ['w01', 'w23'], ['x', 'y', 'w01'],
              ['x', 'w01', 'w23'], ['r', 'w01', 'w23'], ['x', 'y', 'r', 'w01'], ['x', 'r', 'w01', 'w23']]


GTAB = {
    'B': {2: {(0, 1): -2, (1, 1): -2}, 3: {(1, 1): 4}, 6: {(0, 0): 1, (1, 0): 1, (0, 1): 1, (1, 1): 1}, 7: {(1, 0): -2, (1, 1): -2}},
    'G02': {2: {(0, 1): 2, (1, 1): -2}, 3: {(1, 1): 4}, 6: {(0, 0): 1, (1, 0): -1, (0, 1): -1, (1, 1): 1}, 7: {(1, 0): 2, (1, 1): -2}},
    'G021': {2: {(0, 1): 2, (1, 1): 2}, 3: {(1, 1): -4}, 6: {(0, 0): 1, (1, 0): 1, (0, 1): -1, (1, 1): -1}, 7: {(1, 0): -2, (1, 1): 2}},
    'G032': {2: {(0, 1): -2, (1, 1): 2}, 3: {(1, 1): -4}, 6: {(0, 0): 1, (1, 0): -1, (0, 1): 1, (1, 1): -1}, 7: {(1, 0): 2, (1, 1): 2}},
}
GSUP = {
    ('B', -1): SUPPORT_RY,
    ('G02', 1): [['x'], ['r'], ['w01'], ['x', 'r'], ['x', 'w01'], ['x', 'w23'], ['y', 'w23'], ['x', 'r', 'w23'], ['x', 'w01', 'w23'], ['y', 'r', 'w23'], ['y', 'w01', 'w23']],
    ('G02', -1): [['x'], ['r'], ['w01'], ['w23'], ['x', 'r'], ['x', 'w01'], ['r', 'w23'], ['w01', 'w23'], ['x', 'y', 'w23'], ['x', 'y', 'r', 'w23'], ['x', 'y', 'w01', 'w23']],
    ('G021', 1): [['x'], ['w01'], ['x', 'w01'], ['x', 'w23'], ['y', 'w23'], ['r', 'w01'], ['x', 'r', 'w01'], ['x', 'w01', 'w23'], ['y', 'w01', 'w23'], ['x', 'r', 'w01', 'w23'], ['y', 'r', 'w01', 'w23']],
    ('G021', -1): [['x'], ['w01'], ['w23'], ['x', 'w01'], ['r', 'w01'], ['w01', 'w23'], ['x', 'y', 'w23'], ['x', 'r', 'w01'], ['r', 'w01', 'w23'], ['x', 'y', 'w01', 'w23'], ['x', 'y', 'r', 'w01', 'w23']],
    ('G032', -1): [['r'], ['w01'], ['w23'], ['x', 'y'], ['x', 'w23'], ['r', 'w23'], ['w01', 'w23'], ['x', 'y', 'r'], ['x', 'y', 'w01'], ['x', 'r', 'w23'], ['x', 'w01', 'w23']],
}


def group_fit2(beta, frame, ysign):
    """t=1 group (sectors 2,3,6,7 at a common frame, pairs (0,1),(2,3) decoded, w = singlet ANDs): angle function
    -4 beta d_p(w01, w23) on its sector, times (-1)^r (-1)^(y if ysign<0); fitted exactly on the x,y-exclusive domain."""
    tab = GTAB[frame]
    sel = {(1, 0, 0): 2, (1, 0, 1): 3, (0, 1, 0): 6, (0, 1, 1): 7}
    dom, G = [], []
    for x, y in [(0, 0), (1, 0), (0, 1)]:
        for r in (0, 1):
            for a in (0, 1):
                for c in (0, 1):
                    dom.append(dict(x=x, y=y, r=r, w01=a, w23=c))
                    p = sel.get((x, y, r))
                    g = 0.0 if p is None else -4.0 * beta * tab[p].get((a, c), 0)
                    G.append(g * (-1) ** r * (ysign if y else 1))
    for sup in (GSUP[(frame, ysign)], [[]] + GSUP[(frame, ysign)]):
        A = np.array([[(-1) ** sum(d[v] for v in S) for S in sup] for d in dom], float)
        c = np.linalg.lstsq(A, np.array(G), rcond=None)[0]
        if np.abs(A @ c - G).max() < 1e-9:
            break
    assert np.abs(A @ c - G).max() < 1e-9
    return [(S, ci) for S, ci in zip(sup, c) if abs(ci) > 1e-12]


def group_fit(beta, support):
    """t=1 group angle function times (-1)^(r+y) (the cz(F,PR) cz(F,PL) frame flips it back), exact on x,y exclusive."""
    th = {p: -4.0 * beta * s * 2 ** len(prs) for p, prs, s in GROUP}
    dom, G = [], []
    for xy in [(0, 0), (1, 0), (0, 1)]:
        for r in (0, 1):
            for a in (0, 1):
                for c in (0, 1):
                    x, y = xy
                    dom.append(dict(x=x, y=y, r=r, w01=a, w23=c))
                    g = th[2] * x * (1 - r) * c + th[3] * x * r * a * c + th[6] * y * (1 - r) + th[7] * y * r * a
                    G.append(g * (-1) ** (r + y))
    sup = [[]] + support
    A = np.array([[(-1) ** sum(d[v] for v in S) for S in sup] for d in dom], float)
    c = np.linalg.lstsq(A, np.array(G), rcond=None)[0]
    assert np.abs(A @ c - G).max() < 1e-9
    return [(S, ci) for S, ci in zip(sup, c) if abs(ci) > 1e-12]


# ---- selector lines: wires PT, PL, A hold GF(2)-linear functions of (t=1, l=2, a=4); a = [t=A0][l=B0]
def ind(alpha, beta, a0, b0):
    """[t=alpha][l=beta] as (linear mask, constant) over (t, l, a)."""
    # [t=al][l=be] = tl + (al^1) l + (be^1) t + (al^1)(be^1);  tl = a + (a0^1) l + (b0^1) t + (a0^1)(b0^1)
    m = 4 ^ ((a0 ^ 1) << 1) ^ (b0 ^ 1) ^ ((alpha ^ 1) << 1) ^ (beta ^ 1)
    c = ((a0 ^ 1) & (b0 ^ 1)) ^ ((alpha ^ 1) & (beta ^ 1))
    return m, c


def _nbrs(s):
    for i in range(3):
        for j in range(3):
            if i != j:
                s2 = list(s)
                s2[i] ^= s[j]
                yield tuple(s2), (j, i)


def _path(s, t):
    prev = {s: None}
    q = deque([s])
    while q:
        x = q.popleft()
        if x == t:
            break
        for y, mv in _nbrs(x):
            if y not in prev:
                prev[y] = (x, mv)
                q.append(y)
    out = []
    while prev[t] is not None:
        x, mv = prev[t]
        out.append(mv)
        t = x
    return out[::-1]


def line_plan(order, a0, b0):
    """DP over wire states; returns list of states (one per middle) minimising total CX."""
    req = {'s0': [ind(0, 0, a0, b0)[0]], 's4': [ind(0, 1, a0, b0)[0]],
           'g': [ind(1, 0, a0, b0)[0], ind(1, 1, a0, b0)[0]]}
    start = (1, 2, 4)
    allst = set([start])
    q = deque([start])
    while q:
        x = q.popleft()
        for y, _ in _nbrs(x):
            if y not in allst:
                allst.add(y)
                q.append(y)
    allst = sorted(allst)
    dcache = {}

    def dd(s, t):
        if (s, t) not in dcache:
            dcache[(s, t)] = len(_path(s, t))
        return dcache[(s, t)]
    layers = [{start: (0, None)}]
    for m in order:
        nl = {}
        for t in allst:
            if not all(r in t for r in req[m]):
                continue
            for s, (c, _) in layers[-1].items():
                v = c + dd(s, t)
                if t not in nl or nl[t][0] > v:
                    nl[t] = (v, s)
        layers.append(nl)
    best = min(layers[-1], key=lambda s: layers[-1][s][0] + dd(s, start))
    seq = [best]
    for k in range(len(order), 1, -1):
        seq.append(layers[k][seq[-1]][1])
    return seq[::-1]


def build_list(beta, plan, var=None, dec_or=None, anc=None, and_choice=(1, 1), ysign=-1):
    var = {} if var is None else var
    dec_or = {} if dec_or is None else dec_or
    a0, b0 = and_choice
    Lc = L()
    u, v, aq, wa, wb = anc['u'], anc['v'], anc['y'], anc['w01'], anc['w23']
    # parity frame; cz(F,PR) cz(F,PL) merged into the CX (flip the rotation sign for p_r=1 and for p_l=1)
    czk = (PR, PL) if ysign < 0 else (PR,)
    for k in czk:
        Lc.add('sdg', k); Lc.add('cx', F, k); Lc.add('s', k); Lc.add('s', F)
    for k in (PT, PL):
        if k not in czk:
            Lc.add('cx', F, k)
    Lc.add('x', PT); Lc.rccx(PR, PT, u); Lc.add('x', PT)

    def vmap(key):
        Lc.add('x', F); Lc.rccx(u, F, v); Lc.add('x', F)
        Lc.fred(v, q2(0), q2(2), var.get(key, 0))
        Lc.add('x', F); Lc.rccx(u, F, v); Lc.add('x', F)

    def and_line():
        if not a0: Lc.add('x', PT)
        if not b0: Lc.add('x', PL)
        Lc.rccx(PT, PL, aq)
        if not a0: Lc.add('x', PT)
        if not b0: Lc.add('x', PL)

    def ormerged_fred(i, j, key):
        # Fredkin controlled by (f OR u): f=1 frame swap for all sectors + fold swap on the f=0 branch of u sectors
        Lc.add('x', F); Lc.add('x', u); Lc.rccx(u, F, v); Lc.add('x', F); Lc.add('x', u); Lc.add('x', v)
        Lc.fred(v, q2(i), q2(j), var.get(key, 0))
        Lc.add('x', v); Lc.add('x', F); Lc.add('x', u); Lc.rccx(u, F, v); Lc.add('x', F); Lc.add('x', u)

    msteps = [k for k, st in enumerate(plan) if st[0] == 'm']
    start_merge = plan[msteps[0]][2] if len(plan[msteps[0]]) > 2 else None
    end_merge = plan[msteps[-1]][2] if len(plan[msteps[-1]]) > 2 else None
    if start_merge is None:
        vmap('v0')
    line_on = [False]
    W = [PT, PL, aq]
    order = [s[0] for s in plan if s[0] in ('s0', 's4', 'g')]
    states = line_plan(order, a0, b0)
    cur = [(1, 2, 4)]

    def goto(st):
        for (j, i) in _path(cur[0], st):
            Lc.add('cx', W[j], W[i])
        cur[0] = st

    def wire_of(alpha, beta):
        m, c = ind(alpha, beta, a0, b0)
        k = cur[0].index(m)
        return W[k], c          # selector = wire XOR c

    dec = []
    vis = [0]

    def undo(pr):
        i, j = pr
        Lc.add('h', q2(i)); Lc.add('cx', q2(i), q2(j)); dec.remove(pr)

    def ensure(pairs):
        need = set(x for pr in pairs for x in pr)
        for pr in list(dec):
            if tuple(sorted(pr)) not in pairs and (pr[0] in need or pr[1] in need):
                undo(pr)
        have = [tuple(sorted(p)) for p in dec]
        for pr in pairs:
            if pr not in have:
                o = pr[::-1] if dec_or.get((pr, vis[0]), 0) else pr
                i, j = o
                Lc.add('cx', q2(i), q2(j)); Lc.add('h', q2(i)); dec.append(o)

    fk = 0
    mi = 0
    for step in plan:
        vis[0] += 1
        if step[0] == 'm':
            for pr in list(dec):
                undo(pr)
            last = (step is plan[msteps[-1]])
            if last and line_on[0]:
                goto((1, 2, 4))
                and_line()
                line_on[0] = False
            mp = step[2] if len(step) > 2 else None
            for k, (i, j) in enumerate(step[1]):
                if mp == k:
                    ormerged_fred(i, j, ('f', fk))
                else:
                    Lc.fred(F, q2(i), q2(j), var.get(('f', fk), 0))
                fk += 1
            continue
        if not line_on[0]:
            and_line()
            line_on[0] = True
        goto(states[mi]); mi += 1
        if step[0] in ('s0', 's4'):
            ensure([(1, 2)])
            if step[0] == 's0':
                w, c = wire_of(0, 0)
                th = -4.0 * beta * step[1] * 2
            else:
                w, c = wire_of(0, 1)
                th = -4.0 * beta * step[1] * 2 * ysign  # cz(F,PL) frame (ysign<0): implement the negated angle
            terms = {}
            add_and(terms, th, [(w, 1 - c), (q2(1), 1), (q2(2), 1)])
            phase_poly_rx(Lc, terms, F)
        elif step[0] == 'g':
            ensure([(0, 1), (2, 3)])
            Lc.rccx(q2(0), q2(1), wa); Lc.rccx(q2(2), q2(3), wb)
            wx, cx_ = wire_of(1, 0)
            wy, cy_ = wire_of(1, 1)
            qm = dict(x=(wx, cx_), y=(wy, cy_), r=(PR, 0), w01=(wa, 0), w23=(wb, 0))
            terms = {}
            for S, ci in group_fit2(beta, step[1] if len(step) > 1 else 'B', ysign):
                key = frozenset(qm[vv][0] for vv in S)
                sg = (-1) ** sum(qm[vv][1] for vv in S)
                terms[key] = terms.get(key, 0.0) + ci * sg
            phase_poly_rx(Lc, terms, F)
            Lc.rccx(q2(2), q2(3), wb); Lc.rccx(q2(0), q2(1), wa)
    for pr in list(dec):
        undo(pr)
    if line_on[0]:
        goto((1, 2, 4))
        and_line()
    if end_merge is None:
        vmap('v1')
    Lc.add('x', PT); Lc.rccx(PR, PT, u); Lc.add('x', PT)
    for k in (PT, PL):
        if k not in czk:
            Lc.add('cx', F, k)
    for k in czk:
        Lc.add('sdg', F); Lc.add('sdg', k); Lc.add('cx', F, k); Lc.add('s', k)
    return Lc.g
from su2plaq.compress.builder import Builder

PLAN = [('m', [(0, 2)], 0), ('g', 'G02'), ('m', [(0, 1), (2, 3)]), ('s4', -1), ('m', [(1, 3)]), ('s0', 1), ('m', [(0, 1), (2, 3)])]
VAR = {'v0': 0, 'v1': 0, ('f', 0): 1, ('f', 1): 3, ('f', 2): 2, ('f', 3): 0, ('f', 4): 1, ('f', 5): 3}
DEC = {((0, 1), 2): 0, ((2, 3), 2): 1, ((1, 2), 4): 1, ((1, 2), 6): 1}
AND_CHOICE = (0, 1)


def build(spec):
    b = Builder(spec)
    u = b.alloc(1)[0]
    v = b.alloc(1)[0]
    b.free([v])
    y, wa, wb = b.alloc(3)
    anc = dict(u=u, v=v, y=y, w01=wa, w23=wb)
    gs = peephole(build_list(spec.beta, PLAN, var=VAR, dec_or=DEC, anc=anc, and_choice=AND_CHOICE, ysign=-1))
    for n, qs, p in gs:
        if n == 'rz':
            b.rz(p, *qs)
        else:
            getattr(b, n)(*qs)
    b.free([u, y, wa, wb])
    return b
