"""SUMMARY: parity frame + f-controlled qubit-permutation frames (8 Fredkins total, DP-optimal over sector order) + Bell decode + per-sector Gray-code C^3-R_x phase polynomials on a persistent sector one-hot; 200 CX.
DISCOVERY: every parity sector p of fuzzy_ub becomes sigma*c*X_f (x) (Bell projectors) under some f-controlled permutation of the four q2 wires; a DP over sector order and (branch0, branch1) layouts gives 8 Fredkins total (sectors 4,6,2,3,7 share one layout).
DISCOVERY: keep a 6-ancilla one-hot of the parity p alive for the whole circuit (partly in place on the p_t/p_l wires, 24 CX each way); each rank-4 sector then is a 3-control R_x = 8-CX Gray-code phase polynomial with angles +-beta (Lean-friendly).
"""
FAMILY = "F1"
PARENT = None
from su2plaq.compress.builder import Builder

F = 1
PR, PT, PL = 3, 5, 7

PLAN = [('m', [(2, 3), (0, 1)]), (0, [(1, 2)], 1), ('m', [(0, 2)]), (1, [(0, 1)], -1), ('m', [(1, 3)]),
        (5, [(0, 1)], 1), ('m', [(0, 2)]), (2, [(2, 3)], -1), (3, [(0, 1), (2, 3)], 1), (7, [(0, 1)], -1),
        (6, [], 1), (4, [(1, 2)], -1), ('m', [(0, 3), (1, 3), (2, 3)])]


def q2(i):
    return 2 * i


def cswap(b, i, j):
    a, d = q2(i), q2(j)
    b.cx(d, a); b.ccx(F, a, d); b.cx(d, a)


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
