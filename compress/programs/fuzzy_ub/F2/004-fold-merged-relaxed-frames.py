"""SUMMARY: r03-F3-003 r-fold kept, but the t=1 group sits in the 1-swap frame (0 2) using relaxed (spectator-swap) sector forms, the frame walk becomes (0 2) | G | (0 1)(2 3) | S4 | (1 3) | S0 | (0 1)(2 3), the forward fold swap is merged into the first frame swap as one (f OR u)-controlled Fredkin, the fold Paulis become free Z gates, and the one-hot needs only one AND (y = t l): 7 Fredkins in total (6 routing, one of them (f|u)-controlled, + 1 inverse-fold), 12 qubits, 129 CX.
DISCOVERY: every parity sector also accepts 2 "relaxed" frames where P(rho) D_p = c Pi_S(pair) (1 - 2 Pi_S(other pair)); with them the t=1 sectors 2,3,6,7 share the single-swap frame rho = (0 2) with pairing (01)(23) (11-term merged polynomial, 14-CX walk instead of 16), and an exhaustive Dijkstra over (f,u)-controlled swap walks (both sector tracks, any control function) gives 61 Fredkin-equivalent CX as the routing optimum.
DISCOVERY: the fold V0 = SWAP(q2^0,q2^2) on the (u & ~f) branch commutes with every f-controlled frame and with the t=1 rotations, so it merges with any f-controlled (0 2) swap into one Fredkin controlled by v = f OR u (one rccx); its sign c=-1 is fixed for free by Z(v) Z(f) = (-1)^(u ~f) instead of CZ(v,q2^0) CZ(v,q2^1).
DISCOVERY: with y = t&l the four (t,l) lines are linear: ~t~l = 1+t+l+y, ~t l = l+y, t~l = t+y, so the one-hot costs 6 + 4 CX instead of 16, and the group polynomial can use the raw t wire (x = t + y) at the same walk length.
"""
FAMILY = "F2"
PARENT = "r03-F3-003"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F = 1                      # f = q1^b
PR, PT, PL = 3, 5, 7       # parity wires p_r, p_t, p_l after the parity frame


def q2(i):
    return 2 * i


# 7-CX Clifford+T Fredkin on m = [control, a, d] (equal to cswap up to a global phase)
FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]
_INV = {'h': 'h', 's': 'sdg', 'sdg': 's', 't': 'tdg', 'tdg': 't', 'z': 'z', 'cx': 'cx'}
FRED7_DG = [(_INV[g[0]],) + g[1:] for g in FRED7[::-1]]      # starts with cx(d -> a)


def fredkin(b, c, a, d, dagger=False, skip_first=False):
    m = [c, a, d]
    seq = FRED7_DG if dagger else FRED7
    if skip_first:
        seq = seq[1:]
    for g in seq:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def walk(nodes):
    """Closed shortest walk from the empty set through all nodes (frozensets), Hamming metric (Held-Karp)."""
    nodes = list(nodes)
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
    best = min(range(n), key=lambda i: (dp[(full, i)][0] + d(nodes[i], E), i))
    order = []
    mask, i = full, best
    while i is not None:
        order.append(nodes[i])
        _, pi = dp[(mask, i)]
        mask ^= 1 << i
        i = pi
    return order[::-1]


def walk_len(nodes):
    o = walk(nodes)
    if not o:
        return 0
    return len(o[0]) + sum(len(a ^ c) for a, c in zip(o, o[1:])) + len(o[-1])


def phase_poly_rx(b, terms, t):
    """prod_S exp(-i c_S/2 X_t chi_S): H, CX walk into t, Rz, H.  terms: {frozenset(control qubits): angle}."""
    terms = {S: a for S, a in terms.items() if abs(a) > 1e-12}
    b.h(t)
    if frozenset() in terms:
        b.rz(terms[frozenset()], t)
    cur = frozenset()
    for S in walk(sorted([S for S in terms if S], key=lambda s: sorted(s))) + [frozenset()]:
        for q in sorted(cur ^ S):
            b.cx(q, t)
        cur = S
        if S in terms and S:
            b.rz(terms[S], t)
    b.h(t)


def add_and(terms, theta, cs):
    k = len(cs)
    for r in range(k + 1):
        for S in itertools.combinations(cs, r):
            key = frozenset(S)
            terms[key] = terms.get(key, 0.0) + theta * (-1) ** r / 2 ** k


# t=1 sectors in the frame rho = (0 2) (f=1 branch), pairing a = singlet(q2^0,q2^1), c = singlet(q2^2,q2^3):
# P(rho) D_p = c0 + ca Pa + cc Pc + cac Pa Pc  (relaxed forms: 2c(1-2a), 4ac, (1-2a)(1-2c), 2a(1-2c))
GROUP_COEF = {2: (0, 0, 2, -4), 3: (0, 0, 0, 4), 6: (1, -2, -2, 4), 7: (0, 2, 0, -4)}
GV = ['x', 'y', 'r', 'a', 'c']
LINE = {2: lambda x, y, r: x * (1 - r), 3: lambda x, y, r: x * r, 6: lambda x, y, r: y * (1 - r),
        7: lambda x, y, r: y * r}


def to_t_basis(S):
    """x = t~l = t + y: a Walsh set over (x, y, ...) as a set over the wires (t, y, ...)."""
    if 'x' not in S:
        return frozenset(S)
    return (frozenset(S) - {'x'}) ^ frozenset({'t', 'y'})


def group_fit(coef):
    """Walsh weights (unit beta) of sum_p line_p(x,y,r) M_p(a,c) with the x=y=1 don't-care chosen to minimise the
    t-basis CX walk (exact on the reachable domain, x and y exclusive)."""
    pts = list(itertools.product((0, 1), repeat=5))
    subsets = [frozenset(S) for k in range(6) for S in itertools.combinations(GV, k)]
    val = {}
    for p_ in pts:
        x, y, r, a, c = p_
        val[p_] = sum(LINE[p](x, y, r) * (co[0] + co[1] * a + co[2] * c + co[3] * a * c) for p, co in coef.items())
    W = {S: sum(val[q] * (-1) ** sum(q[GV.index(v)] for v in S) for q in pts) / 32 for S in subsets}
    groups = []
    for T in [frozenset(S) for k in range(4) for S in itertools.combinations(['r', 'a', 'c'], k)]:
        grp = [T, T | {'x'}, T | {'y'}, T | {'x', 'y'}]
        sg = [1, -1, -1, 1]
        g = [W[S] for S in grp]
        opts = {}
        for s in [0.0] + [-g[i] * sg[i] for i in range(4)]:
            v = [g[i] + s * sg[i] for i in range(4)]
            w = {grp[i]: v[i] for i in range(4) if abs(v[i]) > 1e-12}
            opts[frozenset(w)] = w
        m = min(len([S for S in k if S]) for k in opts)
        groups.append([opts[k] for k in sorted(opts, key=lambda k: sorted(map(sorted, k)))
                       if len([S for S in k if S]) == m])
    best = None
    for combo in itertools.product(*groups):
        w = {}
        for d in combo:
            w.update(d)
        L = walk_len([to_t_basis(S) for S in w if S])
        if best is None or L < best[0]:
            best = (L, w)
    w = best[1]
    # exactness check on the reachable domain
    for q in pts:
        if q[0] and q[1]:
            continue
        s = sum(wt * (-1) ** sum(q[GV.index(v)] for v in S) for S, wt in w.items())
        assert abs(s - val[q]) < 1e-9
    return w


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    for k in (PR, PT, PL):
        b.cx(F, k)                                   # parity frame
    u = b.alloc(1, "u")[0]
    b.x(PT); b.rccx(PR, PT, u); b.x(PT)              # u = p_r & ~p_t  (sectors 1, 5)
    y = b.alloc(1, "y")[0]
    b.rccx(PT, PL, y)                                # y = t l; all (t,l) lines are linear in (t, l, y)

    dec = []

    def undo(pr):
        i, j = pr
        b.h(q2(i)); b.cx(q2(i), q2(j)); dec.remove(pr)

    def ensure(pairs):
        need = set(x for pr in pairs for x in pr)
        for pr in list(dec):
            if pr not in pairs and (pr[0] in need or pr[1] in need):
                undo(pr)
        for pr in pairs:
            if pr not in dec:
                i, j = pr
                b.cx(q2(i), q2(j)); b.h(q2(i)); dec.append(pr)

    def frame(swaps):
        """f-controlled physical swaps; a swap on a decoded pair cancels the decoder's last CX (dagger Fredkin)."""
        cancel, touched = {}, set()
        for (i, j) in swaps:
            for pr in dec:
                if set(pr) == {i, j} and not (touched & {i, j}):
                    cancel[(i, j)] = pr
            touched |= {i, j}
        for pr in list(dec):
            if pr not in cancel.values() and set(pr) & touched:
                undo(pr)
        for (i, j) in swaps:
            if (i, j) in cancel:
                pr = cancel[(i, j)]
                b.h(q2(pr[0])); dec.remove(pr)
                fredkin(b, F, q2(pr[1]), q2(pr[0]), dagger=True, skip_first=True)
            else:
                fredkin(b, F, q2(i), q2(j))

    def sector(line, pair, cc, negate=False):
        ensure([pair])
        terms = {}
        if negate:
            b.x(line)
        add_and(terms, -4.0 * beta * cc, [line, q2(pair[0]), q2(pair[1])])
        phase_poly_rx(b, terms, F)
        if negate:
            b.x(line)

    # 1) frame (0 2) merged with the forward fold: swap on (f=1) or (f=0 & u) = (f | u)
    v = b.alloc(1, "v")[0]
    b.x(F); b.x(u); b.rccx(F, u, v); b.x(F); b.x(u); b.x(v)      # v = f | u
    b.z(v); b.z(F)                                                 # (-1)^(u & ~f): fold sign c = -1 -> +1
    fredkin(b, v, q2(0), q2(2))
    b.x(v); b.x(F); b.x(u); b.rccx(F, u, v); b.x(F); b.x(u)
    b.free([v])

    # 2) t=1 group 2,3,6,7 in frame rho = (0 2), pairing (01)(23); variables t (wire PT), y, r, a, c
    ensure([(0, 1), (2, 3)])
    wa, wc = b.alloc(1, "wa")[0], b.alloc(1, "wc")[0]
    b.rccx(q2(0), q2(1), wa); b.rccx(q2(2), q2(3), wc)
    qm = dict(t=PT, y=y, r=PR, a=wa, c=wc)
    terms = {}
    for S, wt in group_fit(GROUP_COEF).items():
        key = frozenset(qm[vv] for vv in to_t_basis(S))
        terms[key] = terms.get(key, 0.0) - 4.0 * beta * wt
    phase_poly_rx(b, terms, F)
    b.rccx(q2(2), q2(3), wc); b.rccx(q2(0), q2(1), wa)
    b.free([wc]); b.free([wa])

    # 3) frame (3,0,1,2): sectors 4 (+5 folded), line ~t l = l + y on PL, pair (1,2), M = -2 Pi_12
    frame([(0, 1), (2, 3)])
    b.cx(y, PL)
    sector(PL, (1, 2), -2)

    # 4) frame (1,0,3,2): sectors 0 (+1 folded), line ~t~l = ~(t + l + y) on PT, M = 2 Pi_12
    frame([(1, 3)])
    b.cx(PL, PT)
    sector(PT, (1, 2), 2, negate=True)

    # 5) back to the identity frame
    frame([(0, 1), (2, 3)])
    for pr in list(dec):
        undo(pr)
    b.cx(PL, PT); b.cx(y, PL)
    b.rccx(PT, PL, y)
    b.free([y])

    # 6) inverse fold: (u & ~f)-controlled swap (0 2) with the same sign phase
    v = b.alloc(1, "v")[0]
    b.x(F); b.rccx(u, F, v); b.x(F)
    b.z(v)
    fredkin(b, v, q2(0), q2(2))
    b.x(F); b.rccx(u, F, v); b.x(F)
    b.free([v])

    b.x(PT); b.rccx(PR, PT, u); b.x(PT)
    b.free([u])
    for k in (PR, PT, PL):
        b.cx(F, k)
    return b
