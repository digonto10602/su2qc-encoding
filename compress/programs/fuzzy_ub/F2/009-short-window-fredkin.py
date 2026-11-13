"""SUMMARY: r08-F2-008 datapath unchanged in CX (83: parity frame, L: 0 -> ~p_t&~s_r [(1 3) Fredkin] -> g, a: f&~g [(0 2) Fredkin] -> w01, w23, 9-term open R_x walk with free ends {p_r, p_t, p_l, g}) with every Fredkin a 7-CX 7-T word (T_fixed 80 -> 72, T_eps 646 -> 638) chosen from an exhaustive class-BFS enumeration for the shortest control-line window (3 control CX + 1 T, data-only prefix/suffix run beside the neighbouring rccx's), X-free negated rccx controls (T <-> Tdg swaps), free control order on clean-target rccx, Z gates parked in idle control slots, the parity CX(f -> p_r) moved next to the rccx that last reads s_r, and rz(theta) = rz(theta - k pi/2) S^k with k fixed per term for shorter gridsynth words (k = 2 Z's pushed off the f wire through the walk CX's); depth_CT 1560 -> 1522, 11 qubits.
DISCOVERY: a class-level BFS for the Fredkin (3-qubit Clifford frames modulo left local Cliffords: 6720 classes x 128 masks of the 7 commuting pi/8 rotations <Z_c, Z_aZ_d, X_aX_d>) confirms 7 CX minimal and gives 221184 class paths over 8704 CX orders; with the best rotation placement the control line of the order (1,2)(0,2)(2,1)(0,1)(1,2)(0,2)(1,2) needs only 7 layers (3 control CX + its T, all other gates on the data pair before/after), against 13 for the r08-F3-008 word; in the L -> a leg chain this is the main depth lever (-21 depth_CT) since CX and T are unchanged.
DISCOVERY: rccx with negated controls needs no X gates: negating c1 (used twice) swaps T and Tdg on the parities t+c1 and t+c0+c1, negating c0 swaps them on t+c0 and t+c0+c1 and adds one Z on the target after the final H (a diagonal phase that can be parked in any idle slot of the control line, or cancelled against the CZ(g, f) Z(a)); on a clean target rccx(c0, c1) and rccx(c1, c0) agree on every reachable state, so the a-line compute may read L in its middle CX while the uncompute reads f there.
DISCOVERY: negative: for the 9-term support with free ends {p_r, p_t, p_l, g} no general CX network (any wire as CX target, rotations on any wire) has 8 CX, and all 8 networks with 9 CX target only f, so the 9 rotations are strictly serial on f (depth_CT >= sum of gridsynth word lengths ~ 1400); putting w23 into L (L: g -> g^w23 mid-walk) or both ANDs on the a line (w01 -> w01^w23 -> w23) saves the third ancilla but needs a 10-CX walk (84 CX, 10 qubits).
"""
FAMILY = "F2"
PARENT = "r08-F2-008"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7


def q2(i):
    return 2 * i


FRED = [('cx', 1, 2), ('t', 2), ('h', 1), ('t', 1), ('h', 1), ('s', 2), ('cx', 0, 2), ('t', 0), ('h', 1), ('cx', 2, 1), ('tdg', 2), ('t', 1), ('cx', 0, 1), ('cx', 1, 2), ('tdg', 1), ('tdg', 2), ('cx', 0, 2), ('s', 1), ('h', 1), ('cx', 1, 2), ('s', 1), ('h', 1), ('z', 1), ('s', 2), ('h', 2), ('x', 2), ('z', 2)]
FRED13 = FRED02 = FRED
CSLOT = {((1, 3), False): 1, ((1, 3), True): 1, ((0, 2), False): 1, ((0, 2), True): 1}
INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's', 'h': 'h', 'x': 'x', 'z': 'z', 'cx': 'cx'}


def cswap(b, i, j, ctrl, rev=False, zc=0):
    """7-CX 7-T Fredkin: swap q2^i, q2^j controlled by ctrl; rev: the reversed inverse word.  The diagonal gates of the
    word on the control (its Z_c rotation) and a pending Z on the control line (zc) commute with the word's control CX's;
    they are emitted after control CX number CSLOT[(pair, rev)], where the control line idles."""
    key = (1, 3) if (i, j) == (1, 3) else (0, 2)
    word = FRED13 if key == (1, 3) else FRED02
    m = [ctrl, q2(i), q2(j)]
    seq = [(INV[g[0]],) + g[1:] for g in reversed(word)] if rev else list(word)
    diag = [g for g in seq if g[1:] == (0,)]
    assert all(g[0] in DIAG for g in diag)
    rest = [g for g in seq if g[1:] != (0,)]
    if zc:
        diag.append(('z', 0))
    slot = CSLOT[(key, rev)]
    out, k = [], 0
    if slot == 0:
        out += diag
    for g in rest:
        out.append(g)
        if g[0] == 'cx' and g[1] == 0:
            k += 1
            if k == slot:
                out += diag
    for g in out:
        getattr(b, g[0])(*[m[k] for k in g[1:]])


def rccx_e(b, c0, c1, t, n0=0, n1=0, inv=False, zfix=True):
    """qiskit rccx(c0', c1', t) with c0' = c0 xor n0, c1' = c1 xor n1, as an explicit 3-CX word: the negations are
    T <-> Tdg swaps on the parities that contain the negated control (+ one Z on t for n0), no X gates."""
    T = lambda f: 'tdg' if f else 't'
    Td = lambda f: 't' if f else 'tdg'
    w = [('h', t), ('t', t), ('cx', c1, t), (Td(n1), t), ('cx', c0, t), (T(n0 ^ n1), t), ('cx', c1, t), (Td(n0), t), ('h', t)]
    if n0 and zfix:
        w.append(('z', t))
    if inv:
        w = [(INV[g[0]],) + g[1:] for g in reversed(w)]
    for g in w:
        getattr(b, g[0])(*g[1:])


# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
# support (sets over r=p_r, t=p_t, l=p_l, v=g, w01, w23); no constant term
SUPPORT = [['t'], ['l', 't'], ['r', 't', 'v'], ['l', 'r', 't', 'v'], ['l', 'r', 't', 'w01'], ['r', 't', 'v', 'w01'],
           ['l', 't', 'w23'], ['l', 'r', 't', 'w23'], ['l', 'r', 't', 'w01', 'w23']]
OPEN = ['r', 't', 'l', 'v']
# rz(theta) = rz(theta - k pi/2) S^k (global phase): k fixed offline (beta = 0.61) for the shortest gridsynth word
SHIFT = {frozenset(['t']): 2, frozenset(['l', 't']): 2, frozenset(['r', 't', 'v']): 2, frozenset(['l', 'r', 't', 'v']): 3,
         frozenset(['l', 't', 'w23']): 2, frozenset(['l', 'r', 't', 'w01', 'w23']): 3}
KG = {1: 's', 2: 'z', 3: 'sdg'}


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


def open_order(nodes, M):
    """exact Held-Karp for the open walk: start and end toggles of wires in M are free."""
    nodes = [frozenset(s) for s in nodes]
    n = len(nodes)
    INF = 10 ** 6
    D = [[len(a ^ b) for b in nodes] for a in nodes]
    st = [len(a - M) for a in nodes]
    N = 1 << n
    dp = [[INF] * n for _ in range(N)]
    par = [[-1] * n for _ in range(N)]
    for i in range(n):
        dp[1 << i][i] = st[i]
    for m in range(1, N):
        for j in range(n):
            vj = dp[m][j]
            if vj >= INF or not (m >> j) & 1:
                continue
            for k in range(n):
                if (m >> k) & 1:
                    continue
                w = vj + D[j][k]
                if w < dp[m | 1 << k][k]:
                    dp[m | 1 << k][k] = w
                    par[m | 1 << k][k] = j
    best = min(range(n), key=lambda j: dp[N - 1][j] + st[j])
    order = []
    m, j = N - 1, best
    while j >= 0:
        order.append(nodes[j])
        pj = par[m][j]
        m ^= 1 << j
        j = pj
    return order[::-1]


class Rec:
    """records gates; they are replayed into the Builder after a peephole pass."""
    def __init__(self):
        self.ops = []

    def __getattr__(self, name):
        def f(*args):
            if name == 'rz':
                self.ops.append((name, (args[0],), tuple(args[1:])))
            else:
                self.ops.append((name, (), tuple(args)))
        return f


DIAG = {'z', 's', 'sdg', 't', 'tdg', 'rz'}


def commutes(g, q, h):
    """does the one-qubit gate g on qubit q commute with the gate h (which also acts on q)?"""
    n, _, qs = h
    if g in DIAG:
        return n in DIAG or (n == 'cx' and qs[0] == q)
    if g == 'x':
        return n == 'x' or (n == 'cx' and qs[1] == q)
    return False


def peephole(ops):
    """cancel inverse pairs of one-qubit Cliffords/T (through gates they commute with) and adjacent equal CX pairs.
    Pure gate identities, independent of the angles (the skeleton is the same at every angle pair)."""
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
    """parity CX(f -> k); if cz_after, followed by CZ(k, f) at no CX cost."""
    if cz_after:
        b.sdg(k); b.cx(F, k); b.s(k); b.s(F)
    else:
        b.cx(F, k)


def cz_par(b, k, cz_before):
    """parity CX(f -> k); if cz_before, preceded by CZ(k, f) at no CX cost."""
    if cz_before:
        b.sdg(k); b.cx(F, k); b.s(k); b.sdg(F)
    else:
        b.cx(F, k)


def leg_head(b, L, a, X0, zg):
    """L: 0 -> c2 = ~p_t&~s_r, swap(q2^1,q2^3)[c2], L: c2 -> g = ~p_t&(s_r^s_l), a: 0 -> c1 = f&~g, swap(q2^0,q2^2)[c1].
    zg: CZ(g, f) = Z(f) Z(a) while a holds c1 (the walk's opening g toggle)."""
    if zg:
        b.z(F)
    cx_par(b, PT, PT in X0)
    rccx_e(b, PT, PR, L, 1, 1, zfix=False)
    cx_par(b, PR, PR in X0)                  # raw s_r is not read again
    cswap(b, 1, 3, L, zc=1)
    rccx_e(b, PL, PT, L, 1, 1)
    rccx_e(b, L, F, a, 1, 0, zfix=False)     # clean target: control order free; its Z fix joins the Fredkin
    cx_par(b, PL, PL in X0)
    cswap(b, 0, 2, a, zc=1 ^ zg)


def leg_tail(b, L, a, X1, zg):
    """exact inverse of leg_head (with the closing CZ(g, f) = Z(f) Z(a) if zg)."""
    cswap(b, 0, 2, a, True, zc=1 ^ zg)
    cz_par(b, PL, PL in X1)
    rccx_e(b, L, F, a, 1, 0, True, zfix=False)
    rccx_e(b, PL, PT, L, 1, 1, True)
    cswap(b, 1, 3, L, True, zc=1)
    cz_par(b, PR, PR in X1)
    rccx_e(b, PT, PR, L, 1, 1, True, zfix=False)
    cz_par(b, PT, PT in X1)
    if zg:
        b.z(F)


def decode(b):
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))


def encode(b):
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))


def build(spec):
    B = Builder(spec)
    b = Rec()
    a, g, w23 = B.alloc(3, "agw")
    qm = dict(r=PR, t=PT, l=PL, v=g, w01=a, w23=w23)
    terms = group_terms(spec.beta)
    M = frozenset(OPEN)
    order = open_order([S for S in terms if S], M)
    X0 = frozenset(qm[n] for n in order[0] & M)
    X1 = frozenset(qm[n] for n in order[-1] & M)
    leg_head(b, g, a, X0, g in X0)
    decode(b)
    rccx_e(b, F, g, a, 0, 1, True)          # a: c1 -> 0
    rccx_e(b, q2(0), q2(1), a)              # a: 0 -> w01
    rccx_e(b, q2(2), q2(3), w23)            # w23
    b.h(F)
    cur = X0
    zp = 0      # pending Z on f from the k = 2 shifts: Z_f CX(q -> f) = CX(q -> f) Z_q Z_f, so it leaves Z_q behind on q
    for S in order:
        Sq = frozenset(qm[n] for n in S)
        for q in sorted(cur ^ Sq):
            b.cx(q, F)
            if zp:
                b.z(q)
        cur = Sq
        k = SHIFT.get(S, 0)
        b.rz(terms[S] - k * np.pi / 2, F)
        if k == 2:
            zp ^= 1
        elif k:
            getattr(b, KG[k])(F)
    for q in sorted(cur ^ X1):
        b.cx(q, F)
        if zp:
            b.z(q)
    if zp:
        b.z(F)
    b.h(F)
    rccx_e(b, q2(2), q2(3), w23, inv=True)
    rccx_e(b, q2(0), q2(1), a, inv=True)
    rccx_e(b, F, g, a, 0, 1)
    encode(b)
    leg_tail(b, g, a, X1, g in X1)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g, w23])
    return B
