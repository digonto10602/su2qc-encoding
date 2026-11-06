"""SUMMARY: parity frame, then 8 per-sector sandwiches F_p^dag C^{p,S}R_x(-4 beta sigma_p) F_p with uncontrolled frames (f-controlled q2 permutation + Bell decoders), merged permutations between sectors and Gray-shared rccx ladders.
DISCOVERY: every parity sector p of fuzzy_ub becomes sigma_p X_f (x) |1_S><1_S| after one f-controlled permutation of the four q2 qubits plus 0/1/2 CX+H Bell decoders; perm (3,0,1,2) (q2^i -> pi[i]) serves sectors 2,3,4,6,7 at once.
DISCOVERY: sector frames need no parity control (the middle rotation is identity off-sector), so consecutive frames merge to f-controlled transposition chains; ordered 0,1,2,3,4,6,7,5 only 8 Fredkins (64 CX) are needed in total.
"""
FAMILY = "F2"
PARENT = None

from su2plaq.compress.builder import Builder

F = 1                      # f = q1^b
Q2 = [0, 2, 4, 6]          # q2 of b, r, t, l
PB = [3, 5, 7]             # parity bits p_r, p_t, p_l (after the parity frame)
ID = (0, 1, 2, 3)
# (sector p, f-controlled perm pi (q2 bit i -> pi[i]), Bell-decoder pairs (cx a->b, h a), sigma, excluded p-bit of first rccx)
PLAN = [(0, (1, 0, 3, 2), ((1, 2),), 2, 0), (1, (1, 2, 3, 0), ((0, 1),), -2, 0),
        (2, (3, 0, 1, 2), ((2, 3),), -2, 0), (3, (3, 0, 1, 2), ((0, 1), (2, 3)), 4, 0),
        (4, (3, 0, 1, 2), ((1, 2),), -2, 1), (6, (3, 0, 1, 2), (), 1, 1),
        (7, (3, 0, 1, 2), ((0, 1),), -2, 1), (5, (3, 2, 1, 0), ((0, 1),), 2, 1)]
SELF_INV = {"x", "h", "cx", "ccx", "rccx", "cz", "z", "swap"}


def _inv(a):
    r = [0] * 4
    for i in range(4):
        r[a[i]] = i
    return tuple(r)


def _transpositions(tau):
    """swaps (in time order) moving the content of position i to tau[i]."""
    cur = list(range(4))          # cur[i] = where original content i sits now
    where = {i: i for i in range(4)}
    out = []
    tinv = _inv(tau)
    for j in range(4):
        i = tinv[j]
        k = cur[i]
        if k != j:
            out.append((j, k))
            # contents at j and k exchange
            for m in range(4):
                if cur[m] == j:
                    cur[m] = k
                elif cur[m] == k:
                    cur[m] = j
                    pass
            cur[i] = j
    return out


class _Emit:
    def __init__(self):
        self.g = []

    def add(self, name, qs, params=()):
        qs = tuple(qs)
        if name in SELF_INV:
            for j in range(len(self.g) - 1, -1, -1):
                n2, q2, p2 = self.g[j]
                if n2 == name and q2 == qs:
                    del self.g[j]
                    return
                if set(q2) & set(qs):
                    break
        self.g.append((name, qs, params))


def build(spec):
    b = Builder(spec)
    anc = b.alloc(6, "ladder")
    E = _Emit()
    for t in PB:
        E.add("cx", (F, t))

    def cswap_perm(tau):
        for i, j in _transpositions(tau):
            a, c = Q2[i], Q2[j]
            E.add("cx", (c, a)); E.add("ccx", (F, a, c)); E.add("cx", (c, a))

    def comp(a, c):  # a after c
        return tuple(a[c[i]] for i in range(4))

    cur = ID
    for p, pi, pairs, sig, ex in PLAN:
        cswap_perm(comp(pi, _inv(cur)))
        cur = pi
        for a, c in pairs:
            E.add("cx", (Q2[a], Q2[c])); E.add("h", (Q2[a],))
        bits = [k for k in range(3) if k != ex] + [ex]
        lits = [PB[k] for k in bits]
        neg = [PB[k] for k in range(3) if not (p >> k) & 1]
        for q in neg:
            E.add("x", (q,))
        ctrls = lits + [Q2[q] for pr in pairs for q in pr]
        chain = [(ctrls[0], ctrls[1], anc[0])] + [(ctrls[i], anc[i - 2], anc[i - 1]) for i in range(2, len(ctrls))]
        for c1, c2, t in chain:
            E.add("rccx", (c1, c2, t))
        E.add("crx", (anc[len(ctrls) - 2], F), (-4.0 * sig * spec.beta,))
        for c1, c2, t in reversed(chain):
            E.add("rccx", (c1, c2, t))
        for q in neg:
            E.add("x", (q,))
        for a, c in reversed(pairs):
            E.add("h", (Q2[a],)); E.add("cx", (Q2[a], Q2[c]))
    cswap_perm(_inv(cur))
    for t in PB:
        E.add("cx", (F, t))
    for name, qs, params in E.g:
        getattr(b, name)(*params, *qs)
    b.free(anc)
    return b
