"""SUMMARY: line-free routing: nine Fredkins whose controls are single q1 wires holding affine functions of (f, p_r, p_t, p_l) (6 parity CX in total, no u/e lines, no rccx toggles), tour (0 2)[f^p_l] (0 3)[f] (0 2)[p_r^p_l] (0 1)[f] | t=0 middle (decoder (1,2), 3-control R_x on ~p_t) | (0 1)[f] (0 2)[p_r^p_l] (0 3)[f] (0 2)[p_l] | t=1 group (pairs (0,1),(2,3), 17-term polynomial on (p_r^p_l, p_t, p_l, w01, w23), Gray walk 18) | (0 2)[f]; 113 CX, 10 qubits.
DISCOVERY: affine-controlled q2 swaps fold the four t=0 sectors onto one normal form (singlet on pair (1,2), value -2, same sign) in 4 swaps, e.g. (0 2)[f^p_l],(0 3)[f],(0 2)[p_r^p_l],(0 1)[f]; exhaustive search: no fold with <=3 affine swaps, no closed 8-swap affine tour that also visits a t=1 group frame, but 9-swap tours exist (24576 control/constant variants, middles at positions 4 and 8).
DISCOVERY: an exact shortest-path DP over the GL(4,2) contents of the four q1 wires (each Fredkin needs one wire = its control, each middle needs f on exactly one wire and p_t alone on another) gives 6 parity CX for that tour, so the routing costs 9 x 7 + 6 = 69 CX instead of 6 Fredkins + 24 CX of u/e lines and toggles; the t=1 group frame reached there has a 17-term Walsh support with a Hamiltonian Gray cycle (walk 18 CX, vs 20 at G=(3,0,1,2)).
DISCOVERY: negative results at this tour: the t=0 middle cannot drop its ~p_t control (its singlet rotation transported to the group frame is not diagonal in pairs (0,1),(2,3)); no palindromic 10-swap affine tour puts the t=0 fold and a t=1 group frame at the same point (so no merged middle); one AND ancilla instead of two needs 23 terms (no gain).
"""
FAMILY = "F2"
PARENT = "r04-F2-004"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, R, T, L = 1, 3, 5, 7


def q2(i):
    return 2 * i


FRED7 = [('h', 1), ('s', 1), ('h', 1), ('s', 2), ('t', 2), ('h', 2), ('s', 2), ('h', 2), ('sdg', 2), ('cx', 1, 2),
         ('h', 1), ('s', 1), ('h', 1), ('z', 1), ('t', 1), ('z', 2), ('h', 2), ('t', 2), ('h', 2), ('tdg', 2),
         ('cx', 0, 2), ('t', 2), ('cx', 1, 2), ('tdg', 2), ('cx', 0, 2), ('cx', 0, 1), ('t', 0), ('tdg', 1),
         ('cx', 0, 1), ('t', 2), ('h', 2), ('cx', 2, 1)]


def cswap(b, ctrl, i, j):
    m = [ctrl, q2(i), q2(j)]
    for g in FRED7:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def gray_cycle(nodes):
    nodes = sorted([frozenset(s) for s in nodes if s], key=lambda s: (len(s), sorted(s)))
    n = len(nodes)
    E = frozenset()
    adj = {a: [c for c in nodes if len(a ^ c) == 1] for a in nodes + [E]}
    path, used, cnt = [E], set(), [0]

    def dfs(cur):
        cnt[0] += 1
        if cnt[0] > 500000:
            return False
        if len(used) == n:
            return len(cur) == 1
        for c in adj[cur]:
            if c not in used:
                used.add(c); path.append(c)
                if dfs(c):
                    return True
                used.remove(c); path.pop()
        return False
    if dfs(E):
        return path[1:]
    raise RuntimeError("no Gray cycle")


def phase_poly_rx(b, terms, t, order=None):
    """prod_S exp(-i c_S/2 X_t chi_S): H, CX walk with Rz, H.  terms {frozenset(qubits): c}."""
    terms = {S: a for S, a in terms.items() if abs(a) > 1e-12}
    if order is None:
        order = gray_cycle([S for S in terms if S])
    b.h(t)
    if frozenset() in terms:
        b.rz(terms[frozenset()], t)
    cur = frozenset()
    for S in list(order) + [frozenset()]:
        for q in sorted(cur ^ S):
            b.cx(q, t)
        cur = S
        if S:
            b.rz(terms[S], t)
    b.h(t)


def walsh_terms(fun, qubits):
    """Walsh expansion of fun(bits) over the given qubits -> {frozenset(qubits): coefficient}."""
    n = len(qubits)
    pts = list(itertools.product(range(2), repeat=n))
    vals = np.array([fun(x) for x in pts], float)
    out = {}
    for S in pts:
        c = sum(v * (-1) ** sum(s * x for s, x in zip(S, p)) for v, p in zip(vals, pts)) / 2 ** n
        if abs(c) > 1e-12:
            out[frozenset(q for q, s in zip(qubits, S) if s)] = c
    return out


# Frame data (classical analysis of the parity-sector blocks of the plaquette, scratch/proposer/fub-f2r5):
# after the first eight swaps every t=1 sector is X_f (x) D_p with D_p diagonal after Bell-decoding pairs (0,1),(2,3)
# (decoder cx(i->j), h(i)); w01, w23 = AND of the decoded pair bits.  R_x angle = -4 beta * value (U_B = exp(+2 i beta square)).
# decoded diagonal of the t=1 sectors at the group frame, pairs (0,1),(2,3); key (p_r, p_l) -> d(w01, w23)
GROUP_D = {(0, 0): lambda a, c: 2 * c * (1 - 2 * a),
           (0, 1): lambda a, c: (1 - 2 * a) * (1 - 2 * c),
           (1, 0): lambda a, c: 4 * a * c,
           (1, 1): lambda a, c: 2 * a * (1 - 2 * c)}
T0_D = -2   # common decoded value of the four t=0 sectors on |11> of pair (1,2)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    # wires: F=f, R=f^pr, T=f^pt, L=f^pl (raw)
    b.cx(F, T)            # T = pt
    b.cx(L, R)            # R = pr^pl
    cswap(b, L, 0, 2)     # control f^pl
    b.cx(F, L)            # L = pl
    cswap(b, F, 0, 3)
    cswap(b, R, 0, 2)
    cswap(b, F, 0, 1)
    # M0: t=0 middle, decoder (1,2), R_x on F controlled by ~pt & w1 & w2
    b.cx(q2(1), q2(2)); b.h(q2(1))
    b.x(T)
    th = -4.0 * beta * T0_D
    terms = walsh_terms(lambda x: th * x[0] * x[1] * x[2], [T, q2(1), q2(2)])
    phase_poly_rx(b, terms, F)
    b.x(T)
    b.h(q2(1)); b.cx(q2(1), q2(2))
    cswap(b, F, 0, 1)
    cswap(b, R, 0, 2)
    cswap(b, F, 0, 3)
    cswap(b, L, 0, 2)     # control pl
    # G: group middle
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))
    w01, w23 = b.alloc(2, "w")
    b.rccx(q2(0), q2(1), w01); b.rccx(q2(2), q2(3), w23)
    # wire contents now: R = pr^pl, T = pt, L = pl
    def g(x):
        rv, tv, lv, a, c = x
        pl = lv; pr = rv ^ lv; pt = tv
        if not pt:
            return 0.0
        return -4.0 * beta * GROUP_D[(pr, pl)](a, c)
    terms = walsh_terms(g, [R, T, L, w01, w23])
    phase_poly_rx(b, terms, F)
    b.rccx(q2(2), q2(3), w23); b.rccx(q2(0), q2(1), w01)
    b.free([w01, w23])
    for (i, j) in [(0, 1), (2, 3)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))
    b.cx(F, L)            # L = f^pl
    b.cx(L, R)            # R = f^pr
    b.cx(F, T)            # T = f^pt
    cswap(b, F, 0, 2)
    return b
