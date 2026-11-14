"""SUMMARY: r09-F3-009 10-qubit datapath (parity frame, L: 0 -> ~p_t&~s_r [(1 3) Fredkin] -> g, a: 0 -> f&~g [(0 2) Fredkin] -> 0 -> w23 fused, w01 toggled onto the p_r wire inside the H(f) window, the same 9-term 9-CX open R_x walk with free ends {p_r, p_t, p_l, g}) with the r09-F2-009 leg: 7-CX 7-T Fredkins with the data-bound 7-layer control window, the parity CX(f -> p_r) right after the L compute, X-free negated rccx controls, and every negated-control Z fix folded into the fresh compute / final uncompute as four inverted T phases (no Z parked in a Fredkin window); angle-agnostic rotation words (no nominal-angle shifts); 83 CX, T_eps 638, depth_CT 1546, 10 qubits.
DISCOVERY: depth_CT budget at beta = 0.61 with angle-agnostic words: the 9 serial gridsynth words take 1451 levels (r09-F2-009 1424 and r09-F1-009 1418 only through k pi/2 / pi shifts chosen at the nominal angle); this program is 43 + 1451 + 9 + 43 = 1546, while the r09-F2-009 structure with the same unshifted words would be 43 + 1451 + 11 + 44 = 1549, so the 11th qubit buys no depth and of F2-009's 1522 about 27 levels are nominal-angle word choice.
DISCOVERY: negative: the leg's line chain is forced serial for decoder (01)(23): among the 1024 valid two-swap control pairs none has both controls single ANDs of wire literals (f, s_k or p_k, negations) and none has the second control equal to an AND of a wire literal and a literal of the first line's pre-conversion value, so the a compute cannot overlap the first Fredkin; with every block at its minimum (fresh rccx 9 levels: |+> prep, phase, 3 CX; once-used control in the middle CX: 5-level tail and head; data-bound 7-layer Fredkin window) the path to the first rotation is 9+7+9+5+7+5+1 = 43 levels (and 43 after the last one).
"""
FAMILY = "F3"
PARENT = "r09-F3-009"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7


def q2(i):
    return 2 * i


FRED = [('cx', 1, 2), ('t', 2), ('h', 1), ('t', 1), ('h', 1), ('s', 2), ('cx', 0, 2), ('t', 0), ('h', 1), ('cx', 2, 1), ('tdg', 2), ('t', 1), ('cx', 0, 1), ('cx', 1, 2), ('tdg', 1), ('tdg', 2), ('cx', 0, 2), ('s', 1), ('h', 1), ('cx', 1, 2), ('s', 1), ('h', 1), ('z', 1), ('s', 2), ('h', 2), ('x', 2), ('z', 2)]
INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's', 'h': 'h', 'x': 'x', 'z': 'z', 'cx': 'cx'}
DIAG = {'z', 's', 'sdg', 't', 'tdg', 'rz'}


def cswap(b, i, j, ctrl, rev=False):
    """7-CX 7-T Fredkin swap(q2^i, q2^j)[ctrl] (r09-F2-009 word: control used by 3 CX + its T, all other gates on the
    data pair); rev: the inverse word.  The control's diagonal gate is emitted after its first control CX."""
    m = [ctrl, q2(i), q2(j)]
    seq = [(INV[g[0]],) + g[1:] for g in reversed(FRED)] if rev else list(FRED)
    diag = [g for g in seq if g[1:] == (0,)]
    rest = [g for g in seq if g[1:] != (0,)]
    out, k = [], 0
    for g in rest:
        out.append(g)
        if g[0] == 'cx' and g[1] == 0:
            k += 1
            if k == 1:
                out += diag
    for g in out:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def rccx_w(c0, c1, t, n0=0, n1=0, zfix=True, flip=0):
    """qiskit rccx(c0 ^ n0, c1 ^ n1, t) without X gates (negations = T <-> Tdg swaps, + Z(t) for n0 unless zfix=False);
    flip=1 inverts all four phases = Z(t) after a fresh-target compute (or before a final uncompute to |0>)."""
    T = lambda f: 'tdg' if f ^ flip else 't'
    Td = lambda f: 't' if f ^ flip else 'tdg'
    w = [('h', t), (T(0), t), ('cx', c1, t), (Td(n1), t), ('cx', c0, t), (T(n0 ^ n1), t), ('cx', c1, t), (Td(n0), t), ('h', t)]
    if n0 and zfix:
        w.append(('z', t))
    return w


def emit(b, w, inv=False):
    if inv:
        w = [(INV[g[0]],) + g[1:] for g in reversed(w)]
    for g in w:
        getattr(b, g[0])(*g[1:])


def rccx_e(b, c0, c1, t, n0=0, n1=0, inv=False, zfix=True, flip=0):
    emit(b, rccx_w(c0, c1, t, n0, n1, zfix, flip), inv)


def fused_pair(c0, c1, n1, d0, d1, t):
    """rccx(c0, ~^n1 c1, t) [target -> 0] then rccx(d0, d1, t) [0 -> AND], inner H.H removed, phases merged."""
    u = rccx_w(c0, c1, t, 0, n1)
    v = rccx_w(d0, d1, t)
    ph = {'t': 1, 'tdg': -1}
    comb = ph[u[-2][0]] + ph[v[1][0]]
    mid = [('s', t)] if comb == 2 else ([('sdg', t)] if comb == -2 else [])
    return u[:-2] + mid + v[2:]


LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
SUPPORT = [['r', 't'], ['t', 'v'], ['r', 't', 'l'], ['t', 'l', 'v'], ['r', 't', 'l', 'w01'], ['r', 't', 'v', 'w01'],
           ['t', 'l', 'w23'], ['r', 't', 'l', 'w23'], ['r', 't', 'l', 'w01', 'w23']]
PATH = [('tog', 'X'), ('tog', 'Y'), ('cx', 'PL'), ('cx', 'PR'), ('cx', 'L'), ('cx', 'PL'), ('cx', 'a'), ('cx', 'PR'),
        ('tog', 'X'), ('cx', 'PR'), ('cx', 'a'), ('tog', 'Y'), ('cx', 'PL')]
START = ['PT', 'PL', 'L']


def fit_terms(beta):
    sup = [tuple(S) for S in SUPPORT]
    rows, th = [], []
    for r, t, l, x, y in itertools.product(range(2), repeat=5):
        v = dict(r=r, t=t, l=l, w01=x, w23=y, v=(1 - t) & (r ^ l))
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * l]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9
    return {frozenset(S): ci for S, ci in zip(sup, c)}


class Rec:
    def __init__(self):
        self.ops = []

    def __getattr__(self, name):
        def f(*args):
            if name == 'rz':
                self.ops.append((name, (args[0],), tuple(args[1:])))
            else:
                self.ops.append((name, (), tuple(args)))
        return f


def commutes(g, q, h):
    n, _, qs = h
    if g in DIAG:
        return n in DIAG or (n == 'cx' and qs[0] == q)
    if g == 'x':
        return n == 'x' or (n == 'cx' and qs[1] == q)
    return False


def peephole(ops):
    changed = True
    while changed:
        changed = False
        out = []
        for op in ops:
            n, p, qs = op
            if n in INV and n != 'cx':
                q = qs[0]
                k = len(out) - 1
                hit = False
                while k >= 0:
                    h = out[k]
                    if q in h[2]:
                        if h[0] == INV[n] and h[2] == qs:
                            del out[k]
                            hit = changed = True
                            break
                        if not commutes(n, q, h):
                            break
                    k -= 1
                if not hit:
                    out.append(op)
            elif n == 'cx':
                k = len(out) - 1
                hit = False
                while k >= 0:
                    h = out[k]
                    if set(h[2]) & set(qs):
                        if h == op:
                            del out[k]
                            hit = changed = True
                        break
                    k -= 1
                if not hit:
                    out.append(op)
            else:
                out.append(op)
        ops = out
    return ops


def cx_par(b, k, cz_after):
    if cz_after:
        b.sdg(k); b.cx(F, k); b.s(k); b.s(F)
    else:
        b.cx(F, k)


def cz_par(b, k, cz_before):
    if cz_before:
        b.sdg(k); b.cx(F, k); b.s(k); b.sdg(F)
    else:
        b.cx(F, k)


def leg_head(b, L, a, X0, zg):
    """L: 0 -> c2 = ~p_t&~s_r, swap(q2^1,q2^3)[c2], L: c2 -> g = ~p_t&(s_r^s_l), a: 0 -> c1 = f&~g, swap(q2^0,q2^2)[c1].
    zg: the walk's opening CZ(g, f) = Z(f) Z(a) while a holds c1; its Z(a) cancels the a compute's Z fix."""
    if zg:
        b.z(F)
    cx_par(b, PT, PT in X0)
    rccx_e(b, PT, PR, L, 1, 1, zfix=False, flip=1)    # its Z(L) fix = all phases flipped (fresh target)
    cx_par(b, PR, PR in X0)
    cswap(b, 1, 3, L)
    rccx_e(b, PL, PT, L, 1, 1)
    rccx_e(b, L, F, a, 1, 0, zfix=False, flip=1 ^ zg)
    cx_par(b, PL, PL in X0)
    cswap(b, 0, 2, a)


def leg_tail(b, L, a, X1, zg):
    cswap(b, 0, 2, a, True)
    cz_par(b, PL, PL in X1)
    rccx_e(b, L, F, a, 1, 0, True, zfix=False, flip=1 ^ zg)
    rccx_e(b, PL, PT, L, 1, 1, True)
    cswap(b, 1, 3, L, True)
    cz_par(b, PR, PR in X1)
    rccx_e(b, PT, PR, L, 1, 1, True, zfix=False, flip=1)
    cz_par(b, PT, PT in X1)
    if zg:
        b.z(F)


def decode(b):
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))


def encode(b):
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))


def walk_seq(terms):
    base = dict(PR={'r'}, PT={'t'}, PL={'l'}, L={'v'}, a=set())
    ands = dict(X=('PR', 'w01'), Y=('a', 'w23'))
    val = {k: set(v) for k, v in base.items()}
    cont = set()
    for w in START:
        cont ^= base[w]
    seq, visited = [], set()
    if frozenset(cont) in terms:
        seq.append(('rz', frozenset(cont))); visited.add(frozenset(cont))
    for mv in PATH:
        if mv[0] == 'tog':
            ln, wn = ands[mv[1]]
            val[ln] ^= {wn}
            seq.append(('tog', mv[1]))
        else:
            cont ^= val[mv[1]]
            seq.append(('cx', mv[1]))
            fc = frozenset(cont)
            if fc in terms and fc not in visited:
                seq.append(('rz', fc)); visited.add(fc)
    assert visited == set(terms)
    end = [w for w in ('PR', 'PT', 'PL', 'L') if base[w] <= cont]
    e = set()
    for w in end:
        e ^= base[w]
    assert e == cont
    return seq, end


def build(spec):
    B = Builder(spec)
    b = Rec()
    a, g = B.alloc(2, "ag")
    wire = dict(PR=PR, PT=PT, PL=PL, L=g, a=a)
    terms = fit_terms(spec.beta)
    seq, end = walk_seq(terms)
    X0 = frozenset(wire[w] for w in START if w in ('PR', 'PT', 'PL'))
    X1 = frozenset(wire[w] for w in end if w in ('PR', 'PT', 'PL'))
    zg0, zg1 = 'L' in START, 'L' in end
    W01 = (q2(0), q2(1)); W23 = (q2(2), q2(3))
    leg_head(b, g, a, X0, zg0)
    decode(b)
    ty = [i for i, ev in enumerate(seq) if ev == ('tog', 'Y')]
    assert len(ty) == 2
    emit(b, fused_pair(F, g, 1, W23[0], W23[1], a))          # a: c1 -> 0 -> w23
    b.h(F)
    for i, ev in enumerate(seq):
        if ev[0] == 'rz':
            b.rz(terms[ev[1]], F)
        elif ev[0] == 'cx':
            b.cx(wire[ev[1]], F)
        elif ev == ('tog', 'X'):
            rccx_e(b, W01[0], W01[1], PR)
        elif i not in ty:
            raise AssertionError
    b.h(F)
    emit(b, fused_pair(F, g, 1, W23[0], W23[1], a), inv=True)   # a: w23 -> 0 -> c1
    encode(b)
    leg_tail(b, g, a, X1, zg1)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
