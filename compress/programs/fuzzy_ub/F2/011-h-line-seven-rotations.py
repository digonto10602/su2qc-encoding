"""SUMMARY: T-lean Pareto variant of r10-F2-010 (same leg: parity frame, L: 0 -> ~p_t&~s_r [(1 3) 7-T Fredkin] -> g, a: 0 -> c1 = f&~g [(0 2) Fredkin], Bell decoders (0,1),(2,3), w01 toggled onto p_r inside the H(f) window): the a line is not uncomputed but converted, a: c1 -> p_r&~g by one rccx that reads the raw s_r wire ((f^p_r)&~g cancels the f part of c1, so f is not read; cx(f -> p_r) moved after it), then a fused second toggle with p_r&p_l gives a = h = [p = 3] = p_r p_t ~p_l; with h on a line k0 = [p=3] = (chi_rtl - chi_rtlh)/2 needs 2 Walsh terms instead of 4, so the R_x support is 7 terms (rtl, rtlh, rtlW, rtvW, tlV, rtlV, rtlWV; 6 x 2 beta, 1 x 4 beta; parent per-class k pi/2 shifts reused, no new angle tuning) walked in 9 CX from the free start {t, g} to the free end {r, t, l}, with w23 toggled onto a inside the window (a: h <-> h^w23, self-inverse word); 89 CX (+6: one extra AND pair), T_eps 514 (-124), depth_CT 1246 (-275), 10 qubits.
DISCOVERY: one rccx that reads a raw q1 wire converts an f-dependent Fredkin control c = f&~g into the invariant l&~g (l = p_k, the f parts cancel) at the same 3 CX as its uncompute and without reading f; for this datapath the reachable invariants are p_r~g = r(t|l), p_l~g, their negations, p_t and ~p_t~g, none of which shortens k0 = [p=3] below 4 Walsh terms, but p_r~g ^ p_r p_l = [p=3] exactly, so one extra AND pair (6 CX, 8 T) buys 2 rotations (9 -> 7, about -126 T) and 7 is the floor of the W/V-Walsh form (k0, k1, k2 vanish on some sectors so each needs >= 2 terms, k3 = chi_rtl needs 1).
DISCOVERY: negative: in the 7-term datapath the w23 toggles cannot be fused outside the window (with one inner toggle the f content can hold h without V or V without h but not both), the open-walk Dijkstra over all 64 seven-term supports and every W/V target wire (p_r, p_t, p_l, g, a, fresh line) gives 9 CX at best (only W on p_r with V on a or on a fresh line), and moving the first w01 toggle outside the window before cx(f -> p_r) (free end p_r^w01) does not shorten the 9-term parent walk below 9 either; a Feynman path-sum phase-folding pass (Z_8 kernel of the phase map on all 131 parities present in the parent) finds no T merge in the parent's 72 fixed T.
DISCOVERY: Pareto point (89, 514, 1246, 10) against the key best (83, 638, 1521, 10): same CX MAP-Elites bin (floor(8 log2(CX+1)) = 51) and T bin 72 instead of 74; the a-chain relative phase i^(3h) needs no Clifford fix (it cancels against the mirrored chain).
"""
FAMILY = "F2"
PARENT = "r10-F2-010"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7
ACORR = ''      # no Clifford fix needed: the a-chain phase i^(3h) cancels against the mirrored chain


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
    """L: 0 -> c2 = ~p_t&~s_r, swap(q2^1,q2^3)[c2], L: c2 -> g = ~p_t&(s_r^s_l), a: 0 -> c1 = f&~g, swap(q2^0,q2^2)[c1],
    then a: c1 -> p_r&~g (rccx with the raw s_r wire: (f^p_r)&~g cancels the f part of c1) -> h = [p = 3]
    (rccx(p_r, p_l): p_r~g ^ p_r p_l = p_r p_t ~p_l), the two a toggles fused (Tdg H H T = I).
    zg: CZ(g, f) = Z(f) Z(a) while a holds c1 (the walk's opening g toggle)."""
    if zg:
        b.z(F)
    cx_par(b, PT, PT in X0)
    rccx_e(b, PT, PR, L, 1, 1, zfix=False)
    cswap(b, 1, 3, L, zc=1)
    rccx_e(b, PL, PT, L, 1, 1)
    rccx_e(b, L, F, a, 1, 0, zfix=False)     # clean target: control order free; its Z fix joins the Fredkin
    cx_par(b, PL, PL in X0)
    cswap(b, 0, 2, a, zc=1 ^ zg)
    rccx_e(b, PR, L, a, 0, 1)                # a: c1 -> p_r & ~g   (PR still holds raw s_r)
    cx_par(b, PR, PR in X0)
    rccx_e(b, PR, PL, a)                     # a: p_r~g -> h = p_r p_t ~p_l
    if ACORR:
        getattr(b, ACORR)(a)


def inverse(ops):
    out = []
    for n, p, qs in reversed(ops):
        assert n != 'rz'
        out.append((INV[n], p, qs))
    return out


def decode(b):
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))


def encode(b):
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))


# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
# 7-term support over r, t, l, v = g, h = [p=3], w01, w23: k0 = [p=3] = (chi_rtl - chi_rtlh)/2 (2 terms instead of 4)
SUPPORT = [['r', 't', 'l'], ['r', 't', 'l', 'h'], ['r', 't', 'l', 'w01'], ['r', 't', 'v', 'w01'], ['t', 'l', 'w23'],
           ['r', 't', 'l', 'w23'], ['r', 't', 'l', 'w01', 'w23']]
# window: ('tog', 'X') toggles w01 onto the p_r wire, ('tog', 'Y') toggles w23 onto the a line (a: h <-> h ^ w23);
# ('cx', w) is CX(w -> f); a rotation is placed whenever the f content first equals a support term
PATH = [('tog', 'X'), ('cx', 'PR'), ('cx', 'L'), ('cx', 'PL'), ('cx', 'a'), ('tog', 'Y'), ('cx', 'a'), ('cx', 'PR'),
        ('tog', 'X'), ('cx', 'PR'), ('cx', 'a'), ('tog', 'Y'), ('cx', 'a')]
START = ['PT', 'L']      # opening f content {t, v}: CZ(p_t, f) merged into the parity CX, CZ(g, f) = Z(a) Z(f)
# rz(theta) = rz(theta - k pi/2) S^k (global phase), k per coefficient class theta / beta as in the parent
SHIFT = {1: 2, -1: 3, 2: 0, -2: 2, -4: 3}
KG = {1: 's', 2: 'z', 3: 'sdg'}


def fit_terms(beta):
    sup = [tuple(S) for S in SUPPORT]
    rows, th = [], []
    for r, t, l, x, y in itertools.product(range(2), repeat=5):
        v = dict(r=r, t=t, l=l, w01=x, w23=y, v=(1 - t) & (r ^ l), h=int((r, t, l) == (1, 1, 0)))
        rows.append([(-1) ** sum(v[n] for n in S) for S in sup])
        k = LAM[r + 2 * t + 4 * l]
        W, V = (-1) ** x, (-1) ** y
        th.append(-4.0 * beta * (k[0] + k[1] * W + k[2] * V + k[3] * W * V))
    A = np.array(rows, float)
    c = np.linalg.lstsq(A, np.array(th), rcond=None)[0]
    assert np.abs(A @ c - th).max() < 1e-9, np.abs(A @ c - th).max()
    return {frozenset(S): ci for S, ci in zip(sup, c)}


def schedule(terms, wire):
    base = dict(PR={'r'}, PT={'t'}, PL={'l'}, L={'v'}, a={'h'})
    val = {k: set(v) for k, v in base.items()}
    cont = set()
    for w in START:
        cont ^= base[w]
    seq, visited = [], set()
    if frozenset(cont) in terms:
        seq.append(('rz', frozenset(cont)))
        visited.add(frozenset(cont))
    for mv in PATH:
        if mv[0] == 'tog':
            if mv[1] == 'X':
                val['PR'] ^= {'w01'}
                seq.append(('togX',))
            else:
                val['a'] ^= {'w23'}
                seq.append(('togY',))
        else:
            cont ^= val[mv[1]]
            seq.append(('cx', wire[mv[1]]))
            fc = frozenset(cont)
            if fc in terms and fc not in visited:
                seq.append(('rz', fc))
                visited.add(fc)
    assert visited == set(terms), (visited, set(terms))
    assert all(val[k] == base[k] for k in val)
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
    seq, end = schedule(terms, wire)
    X0 = frozenset(wire[w] for w in START if w != 'L')
    X1 = frozenset(wire[w] for w in end if w != 'L')
    zg0, zg1 = 'L' in START, 'L' in end
    leg_head(b, g, a, X0, zg0)
    decode(b)
    b.h(F)
    zp = 0
    for ev in seq:
        if ev[0] == 'cx':
            b.cx(ev[1], F)
            if zp:
                b.z(ev[1])
        elif ev[0] == 'togX':
            rccx_e(b, q2(0), q2(1), PR)     # PR: p_r <-> p_r ^ w01 (self-inverse word; phases cancel in pairs)
        elif ev[0] == 'togY':
            rccx_e(b, q2(2), q2(3), a)      # a: h <-> h ^ w23 (self-inverse word; a is only a control in between)
        else:
            c = terms[ev[1]]
            k = SHIFT.get(int(round(c / spec.beta)), 0)
            b.rz(c - k * np.pi / 2, F)
            if k == 2:
                zp ^= 1
            elif k:
                if zp:
                    getattr(b, KG[(k + 2) % 4])(F)
                    zp = 0
                else:
                    getattr(b, KG[k])(F)
    if zp:
        b.z(F)
    b.h(F)
    encode(b)
    t = Rec()
    leg_head(t, g, a, X1, zg1)
    b.ops += inverse(t.ops)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
