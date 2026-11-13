"""SUMMARY: r08-F1-008 leg (Pauli-scheduled q2 block, 16 CX and two 7-T Fredkins per leg) with the r08-F2-008 g free walk end (CZ(g, f) = Z(a) Z(f) while a = f&~g; 9-CX open walk), 83 CX, T_eps 638, plus two depth-only rewrites (depth_CT 1557 -> 1523): every walk rotation is emitted as rz(+-theta + j pi) with j picked for the shortest pygridsynth word (even j = global phase; the odd-j rotations form an even set whose parities XOR to {p_l, p_r, g}, fixed by Z on those idle control wires; the sign of the last 6 rotations is flipped by one x(f) inside the walk, the closing x(f) cancels the z(f) of the g toggle), and negated rccx controls are realised by T/Tdg sign flips instead of X gates (c1: flip r2, r3; c0: flip r1, r2 with Z(t) before, trivial on a clean target, or r3, r4 with Z(t) after, an invariant line phase that commutes with the walk and is dropped).
DISCOVERY: negative: the 8-CX q2 skeleton floor of r08-F1-008 survives relaxing the middle frame: IDA* (54 CX cosets, local Cliffords and wire labels free, admissible bound = max over pending Paulis of weight - 1) with the w01 and w23 toggles as separately scheduled 3-CX line patterns (Q, P, Q with P, Q in G01 resp. G23 weight-1 at their CX times), and even with w steps allowed before pending Fredkin rotations whose Paulis commute with them, finds no skeleton with <= 7 CX (9.6e8 nodes at bound 7), so 16 + 6 CX per leg is the floor of line-target patterns.
DISCOVERY: rz(theta + j pi) = rz(theta) (-i Z_f)^j, and inside the R_x walk Z_f = Z of the parity f currently holds, so an even set of odd pi shifts costs only Z on the XOR of their parities (control wires, off the critical path) and an x(f) flips the sign of all later rotations; with 2 pi shifts (pure global phase) this picks among ~8 gridsynth words per angle at equal T (0.61: 157 -> 155, -0.61: 164 -> 156): -26 depth_CT here, -34 together with the x(f) sign block and the rccx sign flips.
DISCOVERY: negative (walk side): the target's Pauli symmetries are only the q1 parities and X^4, Z^4 on the q2 wires, and no single controlled-Pauli gate, SWAP, or product of two controlled-Pauli gates on q2 commutes with it (no free skeleton prefix); making w01 a free walk end needs a 7th CX on the fused c1 -> w01 pair (exhaustive <= 6-CX search over line paths and rotation offsets), and the free re-encoding a = w01 ^ g or merging w01/w23 into L gives walks of >= 11 CX, so 9 stays.
"""
FAMILY = "F1"
PARENT = "r08-F1-008"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7

# q2 skeleton of one leg (r08-F1-008; wires 0..3 = q2 of links b, r, t, l; wire 4 = line L, wire 5 = line a)
SEG_A = [('t', 4), ('cx', 0, 2), ('h', 0), ('t', 0), ('t', 2), ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 0), ('tdg', 0), ('cx', 1, 3), ('h', 1), ('t', 1), ('t', 3), ('cx', 1, 4), ('tdg', 4), ('cx', 3, 4), ('t', 4), ('cx', 1, 4), ('tdg', 4), ('cx', 3, 4), ('s', 0), ('h', 0), ('h', 2), ('s', 2), ('h', 2), ('h', 1)]
SEG_B = [('t', 5), ('h', 2), ('cx', 2, 5), ('tdg', 5), ('h', 0), ('cx', 0, 5), ('tdg', 5), ('cx', 2, 5), ('t', 5), ('cx', 0, 5), ('h', 2), ('h', 0)]
SEG_C = [('h', 3), ('cx', 1, 3), ('h', 1), ('tdg', 1), ('z', 1), ('cx', 0, 1), ('s', 0), ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 2), ('s', 2), ('h', 2), ('h', 3), ('s', 3), ('cx', 2, 3), ('h', 1), ('h', 2), ('sdg', 2), ('h', 2), ('cx', 1, 2), ('s', 3), ('h', 3), ('sdg', 1), ('h', 1), ('h', 2)]
# middle frame (end of SEG_C): w01 = AND of the negated skeleton wires 1, 0; w23 = AND of wires 3, 2
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
SUPPORT = [['t'], ['l', 't'], ['r', 't', 'v'], ['l', 'r', 't', 'v'], ['l', 'r', 't', 'w01'], ['r', 't', 'v', 'w01'],
           ['l', 't', 'w23'], ['l', 'r', 't', 'w23'], ['l', 'r', 't', 'w01', 'w23']]
# open walk (9 CX): free ends r, t, l (parity CX(f -> wire)) and v = g (Z(a) Z(f) while a = f & ~g)
ORDER = ['t', 'lt', 'ltw23', 'lrtw23', 'lrtw01w23', 'lrtw01', 'rtvw01', 'rtv', 'lrtv']
OPEN = frozenset(['r', 't', 'l', 'v'])
# emitted angle = SIGN * theta + J * pi (exact up to the global phase and the Z correction below); SIGN = -1 from position
# FLIP on (an x(f) there and one at the walk end, the latter cancels the z(f) of the closing g toggle)
J = [-1, -1, -3, -3, 0, -3, -3, -1, -1]
FLIP = 3
INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's', 'h': 'h', 'x': 'x', 'z': 'z', 'cx': 'cx'}
STD = ['t', 'tdg', 't', 'tdg']
FL = {'t': 'tdg', 'tdg': 't'}


def parse(name):
    out, s = [], name
    for tok in ('w01', 'w23'):
        if tok in s:
            out.append(tok); s = s.replace(tok, '')
    return frozenset(out + list(s))


def group_terms(beta):
    sup = [[]] + SUPPORT
    rows, th = [], []
    for r, t, l, x, y in itertools.product(range(2), repeat=5):
        v = dict(r=r, t=t, l=l, w01=x, w23=y, v=(1 - t) & (r ^ l))
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * l]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9, np.abs(A @ c - th).max()
    return {frozenset(S): ci for S, ci in zip(sup, c) if abs(ci) > 1e-12}


def tog(c0, c1, t, n0=False, n1=False, mode='before'):
    """rccx(c0, c1 -> t) with negated controls by T/Tdg sign flips instead of X gates; a negated c0 leaves Z(t) before
    (mode 'before', trivial on a clean target) or after (mode 'after', a phase on the new line value) -- dropped."""
    r = list(STD)
    idx = ([1, 2] if n1 else []) + (([0, 1] if mode == 'before' else [2, 3]) if n0 else [])
    for i in idx:
        r[i] = FL[r[i]]
    return [('h', t), (r[0], t), ('cx', c1, t), (r[1], t), ('cx', c0, t), (r[2], t), ('cx', c1, t), (r[3], t), ('h', t)]


def fuse(ops):
    """merge adjacent t/tdg gates on the same qubit (t tdg -> nothing, t t -> s, tdg tdg -> sdg)."""
    val = {'t': 1, 'tdg': -1}
    name = {0: None, 2: 's', -2: 'sdg'}
    out = []
    for o in ops:
        if out and o[0] in val and out[-1][0] in val and o[1] == out[-1][1]:
            v = val[o[0]] + val[out.pop()[0]]
            if name[v]:
                out.append((name[v], o[1]))
            continue
        out.append(o)
    return out


def remap(seg, wm):
    return [(o[0],) + tuple(wm[q] for q in o[1:]) for o in seg]


def par(k, cz):
    """parity CX(f -> k), with CZ(k, f) after it at no CX cost if cz."""
    return [('sdg', k), ('cx', F, k), ('s', k), ('s', F)] if cz else [('cx', F, k)]


def head_ops(L, a, X, wm):
    ops = []
    ops += par(PT, PT in X)
    ops += tog(PT, PR, L, True, True, 'before')            # L: 0 -> c2 = ~p_t & ~s_r
    ops += remap(SEG_A, wm)                                 # (1 3) Fredkin on L
    ops += tog(PL, PT, L, True, True, 'after')              # L: c2 -> g = ~p_t & (p_r ^ p_l)  (Z(L) phase (-1)^g dropped)
    ops += par(PL, PL in X)
    ops += tog(F, L, a, False, True)                        # a: 0 -> c1 = f & ~g
    ops += remap(SEG_B, wm)                                 # (0 2) Fredkin on a
    ops += par(PR, PR in X)
    ops += remap(SEG_C, wm)
    return ops


def middle_ops(L, a, w23, wm):
    """a: c1 -> 0 -> w01 (fused), w23: 0 -> AND; Z(a) after the fused pair = (-1)^w01 dropped."""
    first = tog(F, L, a, False, True)
    second = tog(wm[1], wm[0], a, True, True, 'after')     # c0 = ~wire1, c1 = ~wire0 (w01), as in r08-F1-008
    pair = first[:-1] + second[1:]
    ops = fuse(pair)
    ops += tog(wm[3], wm[2], w23)
    return ops


def inverse(ops):
    return [(INV[o[0]],) + tuple(o[1:]) for o in reversed(ops)]


def emit(b, ops):
    for o in ops:
        getattr(b, o[0])(*o[1:])


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    a, g, w23 = b.alloc(3, "agw")
    wm = {0: 0, 1: 2, 2: 4, 3: 6, 4: g, 5: a}
    qm = dict(r=PR, t=PT, l=PL, v=g, w01=a, w23=w23)
    terms = group_terms(beta)
    order = [parse(n) for n in ORDER]
    assert set(order) == set(S for S in terms if S)
    cost = len(order[0] - OPEN) + len(order[-1] - OPEN) + sum(len(x ^ y) for x, y in zip(order, order[1:]))
    assert cost == 9, cost
    X0 = frozenset(qm[n] for n in order[0] & OPEN)
    X1 = frozenset(qm[n] for n in order[-1] & OPEN)
    assert g not in X0 and g in X1
    emit(b, head_ops(g, a, X0, wm))
    mid = middle_ops(g, a, w23, wm)
    emit(b, mid)
    # ---- R_x phase polynomial on f (open walk; the X0 / X1 toggles live in the legs)
    b.h(F)
    odd = frozenset()
    for S, j in zip(order, J):
        if j % 2:
            odd = odd ^ S
    assert sum(j % 2 for j in J) % 2 == 0
    for n in sorted(odd):                       # Z correction of the odd pi shifts: Z on the XOR of their parities
        b.z(qm[n])
    cur = X0
    for i, (S, j) in enumerate(zip(order, J)):
        Sq = frozenset(qm[n] for n in S)
        for q in sorted(cur ^ Sq):
            b.cx(q, F)
        cur = Sq
        if i == FLIP:
            b.x(F)
        sgn = -1.0 if i >= FLIP else 1.0
        b.rz(sgn * terms[S] + np.pi * j, F)
    for q in sorted(cur ^ X1):
        b.cx(q, F)
    # x(F) at the walk end = z(F) after h(F): cancels the z(F) of the closing CZ(g, f) = Z(a) Z(f)
    b.h(F)
    emit(b, inverse(mid))
    b.z(a)
    emit(b, inverse(head_ops(g, a, X1, wm)))
    b.free([a, g, w23])
    return b
