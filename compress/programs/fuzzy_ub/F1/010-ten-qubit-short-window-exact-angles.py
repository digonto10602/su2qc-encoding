"""SUMMARY: r09-F2-009 leg (parity frame, L: 0 -> ~p_t&~s_r [(1 3) short-window 7-CX 7-T Fredkin] -> g, a: f&~g [(0 2) short-window Fredkin], Bell decoders) with the r09-F3-009 10-qubit middle (a: c1 -> 0 -> w23 fused, w01 toggled onto the p_r wire inside the H(f) window, 9-term open R_x walk with free ends {p_t, p_l, g} in, {p_r, p_t} out), so the w23 ancilla is gone; every rotation is emitted at its exact Walsh angle (no angle-specific word shifts), 83 CX, T_eps 638, depth_CT 1546, 10 qubits (like-for-like without word shifts: r09-F2-009 1546 at 11 qubits, r09-F3-009 1550 at 10).
DISCOVERY: the 7-CX short-window Fredkins of r09-F2-009 and the in-window w01 -> p_r toggle of r09-F3-009 compose unchanged: the window toggle is a palindromic rccx pair on a wire that is only a CX control in between (its relative phase cancels exactly), and the F2 decoded frame defines w01 = AND(q2^b, q2^r), w23 = AND(q2^t, q2^l) without negations, so the F3 walk path fits the F2 legs directly (valid at all three angle pairs on the first try).
DISCOVERY: depth floor of this datapath without angle tuning: the f-critical leg chain is rccx 9 + window 7 + rccx 9 + a-compute 5 + window 7 + a-uncompute 5 = 42 layers per side (L-critical rccx read once in the middle, f read once in the middle of the uncompute; all 256 Fredkin diag-slot choices tried, the current one is best), the walk is 9 serial CX on f plus the exact-angle words (1467 layers); a rotation subset that vanishes on g = 0 sectors would let the a-uncompute slide into the walk, but no subset of the minimal 9-term supports does (the g = 0 restriction only has the dependencies {0, t, rl, trl} and {r, rt, l, rtl}, times w parts).
"""
FAMILY = "F1"
PARENT = "r09-F1-009"
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


LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
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



# 10-qubit window (r09-F3-009): w01 toggled onto the p_r wire inside the H(f) window, w23 on the a line after c1 is cleared
SUPPORT10 = [['r', 't'], ['t', 'v'], ['r', 't', 'l'], ['t', 'l', 'v'], ['r', 't', 'l', 'w01'], ['r', 't', 'v', 'w01'],
             ['t', 'l', 'w23'], ['r', 't', 'l', 'w23'], ['r', 't', 'l', 'w01', 'w23']]
PATH = [('tog', 'X'), ('tog', 'Y'), ('cx', 'PL'), ('cx', 'PR'), ('cx', 'L'), ('cx', 'PL'), ('cx', 'a'), ('cx', 'PR'),
        ('tog', 'X'), ('cx', 'PR'), ('cx', 'a'), ('tog', 'Y'), ('cx', 'PL')]
START = ['PT', 'PL', 'L']


def fit_terms(beta, support):
    sup = [tuple(S) for S in support]
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
    return {frozenset(S): ci for S, ci in zip(sup, c)}


def window(beta, a, g):
    wire = dict(PR=PR, PT=PT, PL=PL, L=g, a=a)
    base = dict(PR={'r'}, PT={'t'}, PL={'l'}, L={'v'}, a=set())
    terms = fit_terms(beta, SUPPORT10)
    val = {k: set(v) for k, v in base.items()}
    cont = set()
    for w in START:
        cont ^= base[w]
    seq, visited = [], set()
    if frozenset(cont) in terms:
        seq.append(('rz', frozenset(cont))); visited.add(frozenset(cont))
    for mv in PATH:
        if mv[0] == 'tog':
            ln, wn = ('PR', 'w01') if mv[1] == 'X' else ('a', 'w23')
            first = wn not in val[ln]
            val[ln] ^= {wn}
            seq.append(('tog', mv[1], first))
        else:
            cont ^= val[mv[1]]
            seq.append(('cx', wire[mv[1]]))
            fc = frozenset(cont)
            if fc in terms and fc not in visited:
                seq.append(('rz', fc)); visited.add(fc)
    assert visited == set(terms)
    assert all(val[k] == base[k] for k in val)
    end = [w for w in ('PR', 'PT', 'PL', 'L') if base[w] <= cont]
    e = set()
    for w in end:
        e ^= base[w]
    assert e == cont
    X0 = frozenset(wire[w] for w in START if w in ('PR', 'PT', 'PL'))
    X1 = frozenset(wire[w] for w in end if w in ('PR', 'PT', 'PL'))
    return terms, seq, X0, X1, 'L' in START, 'L' in end


def build(spec):
    B = Builder(spec)
    b = Rec()
    a, g = B.alloc(2, "ag")
    terms, seq, X0, X1, zg0, zg1 = window(spec.beta, a, g)
    tY = [i for i, ev in enumerate(seq) if ev[0] == 'tog' and ev[1] == 'Y']
    assert not any(ev[0] == 'cx' and ev[1] == a for ev in seq[:tY[0]] + seq[tY[-1]:])
    leg_head(b, g, a, X0, zg0)
    decode(b)
    rccx_e(b, F, g, a, 0, 1, True)          # a: c1 -> 0
    rccx_e(b, q2(2), q2(3), a)              # a: 0 -> w23
    b.h(F)
    for i, ev in enumerate(seq):
        if ev[0] == 'rz':
            b.rz(terms[ev[1]], F)
        elif ev[0] == 'cx':
            b.cx(ev[1], F)
        elif ev[1] == 'X':
            rccx_e(b, q2(0), q2(1), PR, inv=not ev[2])   # p_r wire: p_r -> p_r ^ w01 -> p_r (exact inverse pair)
    b.h(F)
    rccx_e(b, q2(2), q2(3), a, inv=True)
    rccx_e(b, F, g, a, 0, 1)
    encode(b)
    leg_tail(b, g, a, X1, zg1)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
