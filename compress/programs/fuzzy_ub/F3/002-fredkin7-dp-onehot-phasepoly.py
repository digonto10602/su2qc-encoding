"""SUMMARY: F1 layout (parity frame, 8 f-controlled Fredkins DP-ordered over sectors, Bell decode, persistent sector one-hot, Gray-code C^3-R_x middles) with each Fredkin emitted as a 7-CX Clifford+T circuit instead of cx+ccx+cx (8 CX); 192 CX.
DISCOVERY: no global routing exists for fuzzy_ub with <=4 controlled q2 swaps even when controls may be any GF(2)-linear function of (f, p_r, p_t, p_l) and uncontrolled relabels are free (exhaustive BFS over 12.7M distinct routings); the condition per sector is only on the relative element g0^-1 g1, whose allowed set R_p has 2 elements (8 for p3, 1 for p6).
DISCOVERY: a Fredkin costs 7 CX (Clifford+T, 9 T) rather than the 8 of cx+ccx+cx; it applies to every f-controlled q2 swap of the routing families.
"""
FAMILY = "F3"
PARENT = "r01-F3-001"
from su2plaq.compress.builder import Builder

F = 1
PR, PT, PL = 3, 5, 7

PLAN = [('m', [(2, 3), (0, 1)]), (0, [(1, 2)], 1), ('m', [(0, 2)]), (1, [(0, 1)], -1), ('m', [(1, 3)]),
        (5, [(0, 1)], 1), ('m', [(0, 2)]), (2, [(2, 3)], -1), (3, [(0, 1), (2, 3)], 1), (7, [(0, 1)], -1),
        (6, [], 1), (4, [(1, 2)], -1), ('m', [(0, 3), (1, 3), (2, 3)])]


def q2(i):
    return 2 * i


FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]


def cswap(b, i, j):
    """Fredkin (control F, swap q2(i), q2(j)) with 7 CX, exact up to a global phase."""
    m = [F, q2(i), q2(j)]
    for g in FRED7:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def mc_rx_pp(b, theta, cs, t):
    """C^n R_x(theta) on t, controls cs (all on |1>), as a Gray-code phase polynomial (2^n CX)."""
    n = len(cs)
    b.h(t)
    g = [k ^ (k >> 1) for k in range(2 ** n)]
    for idx, s in enumerate(g):
        b.rz(theta * (-1) ** bin(s).count('1') / 2 ** n, t)
        nxt = g[(idx + 1) % len(g)]
        bit = (s ^ nxt).bit_length() - 1
        b.cx(cs[bit], t)
    b.h(t)


def onehot(b, anc, inverse=False):
    """Sector one-hot b_p = [p_r p_t p_l == p] in clean ancillas, partly in place on the p_t/p_l wires.
    Returns map p -> qubit."""
    a11, a00 = anc[0], anc[1]
    ops = [('rccx', PT, PL, a11), ('cx', a11, PT), ('cx', a11, PL),          # PT <- t&~l, PL <- l&~t
           ('cx', PT, a00), ('cx', PL, a00), ('cx', a11, a00), ('x', a00)]   # a00 <- ~t&~l
    where = {}
    for k, (q, tl) in enumerate([(a11, 6), (PT, 2), (PL, 4), (a00, 0)]):
        b1 = anc[2 + k]
        ops += [('rccx', q, PR, b1), ('cx', b1, q)]                            # b1 <- q&r, q <- q&~r
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
    anc = b.alloc(6, "onehot")
    hot = onehot(b, anc)
    dec = []

    def undo(pr):
        i, j = pr
        b.h(q2(i)); b.cx(q2(i), q2(j)); dec.remove(pr)

    for step in PLAN:
        if step[0] == 'm':
            for pr in list(dec): undo(pr)
            for i, j in step[1]: cswap(b, i, j)
            continue
        p, pairs, s = step
        need = set(x for pr in pairs for x in pr)
        for pr in list(dec):
            if pr not in pairs and (pr[0] in need or pr[1] in need): undo(pr)
        for pr in pairs:
            if pr not in dec:
                i, j = pr; b.cx(q2(i), q2(j)); b.h(q2(i)); dec.append(pr)
        theta = -4.0 * beta * s * 2 ** len(pairs)
        flags = [q2(x) for pr in pairs for x in pr]
        if len(pairs) == 0:
            b.crx(theta, hot[p], F)
        elif len(pairs) == 1:
            mc_rx_pp(b, theta, [hot[p]] + flags, F)
        else:
            w = b.alloc(2)
            b.rccx(flags[0], flags[1], w[0]); b.rccx(flags[2], flags[3], w[1])
            mc_rx_pp(b, theta, [hot[p], w[0], w[1]], F)
            b.rccx(flags[2], flags[3], w[1]); b.rccx(flags[0], flags[1], w[0])
            b.free(w)
    for pr in list(dec): undo(pr)
    onehot(b, anc, inverse=True)
    b.free(anc)
    for k in (PR, PT, PL): b.cx(F, k)
    return b
