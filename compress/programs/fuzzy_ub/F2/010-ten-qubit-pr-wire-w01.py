"""SUMMARY: r09-F2-009 leg unchanged (parity frame, L: 0 -> ~p_t&~s_r [(1 3) short-window 7-T Fredkin] -> g = ~p_t&(p_r^p_l), a: f&~g [(0 2) Fredkin], X-free negated rccx, Bell decoders (0,1),(2,3)) with the r09-F3-009 ten-qubit middle: the w23 line is dropped, w23 is toggled onto a fused with the c1 uncompute (a: c1 -> 0 -> w23, Tdg H H T = I) and w01 = q2^0&q2^1 is toggled onto the p_r wire inside the H(f) window (self-inverse rccx word around p_r-diagonal walk segments, phases cancel), 9-term R_x support (rt, tv, rtl, tlv, rtlW, rtvW, tlV, rtlV, rtlWV) walked in 9 CX from the free start {t, l, g} to the free end {r, t}; the parent's rz(theta - k pi/2) S^k shift is kept per coefficient class theta/beta (same 4 x beta, 4 x 2 beta, 1 x 4 beta multiset, no new angle tuning), and the pending Z(f) of the k = 2 shifts is absorbed into the next odd-k phase gate (Z S^3 = S) instead of a closing Z(f) on the critical path; 83 CX, T_eps 638, depth_CT 1522 -> 1521, qubits 11 -> 10.
DISCOVERY: the F3-009 middle (w01 on the p_r wire, w23 fused onto a) and the F2-009 leg (short-window Fredkins, plain Bell decoders, un-negated w ANDs) compose without any change of either: both Walsh supports have the identical (sign, magnitude) multiset of the 9 rotation angles (+-beta, +-2 beta, -4 beta in the same counts), so the gridsynth word lengths are equal and the parent's depth carries over while the third ancilla disappears (83, 638, 1521, 10).
DISCOVERY: a pending Z(f) left by the even (k = 2) angle shifts need not close the walk: Z S^k = S^(k+2) on f, so any later odd-k term absorbs it into its own phase gate at no cost (Z's pushed through the walk CX's still land on idle control wires), which removes the closing Z(f) from the critical path (-1 depth_CT) whenever an odd-k term follows the last even one.
DISCOVERY: negative: the leg chain is tight at 42 layers per side for this datapath (L rccx 9 + (1 3) window 7 + L conversion 9 + a-compute after L 5 + (0 2) window 7 + uncompute until f is read 5): any phase-polynomial realisation of the a uncompute (alone or fused with the w23 toggle) needs the two f-free parities of the coset y + span{f, g} before its single f toggle, so f is read at the 2nd CX at the earliest (H, T, CX, T, CX); with free walk start and end every 9-CX walk has exactly one 2-step on f.
"""
FAMILY = "F2"
PARENT = "r09-F2-009"
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




# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
# Walsh support over r=p_r, t=p_t, l=p_l, v=g, w01, w23 (k0 support (rt, tv, rtl, tlv); no constant term)
SUPPORT = [['r', 't'], ['t', 'v'], ['r', 't', 'l'], ['t', 'l', 'v'], ['r', 't', 'l', 'w01'], ['r', 't', 'v', 'w01'],
           ['t', 'l', 'w23'], ['r', 't', 'l', 'w23'], ['r', 't', 'l', 'w01', 'w23']]
# window schedule: ('tog', 'X') toggles w01 into the p_r wire, ('tog', 'Y') toggles w23 into the a line (its first and
# last toggles are fused with the c1 uncompute / recompute outside the H(f) window); ('cx', w) is CX(w -> f); a rotation
# is placed whenever the f content first equals a support term
PATH = [('tog', 'X'), ('tog', 'Y'), ('cx', 'PL'), ('cx', 'PR'), ('cx', 'L'), ('cx', 'PL'), ('cx', 'a'), ('cx', 'PR'),
        ('tog', 'X'), ('cx', 'PR'), ('cx', 'a'), ('tog', 'Y'), ('cx', 'PL')]
START = ['PT', 'PL', 'L']    # opening f content {t, l, v}: CZ(k, f) merged into the parity CX, CZ(g, f) = Z(a) Z(f)
# rz(theta) = rz(theta - k pi/2) S^k (global phase), k per coefficient class theta / beta exactly as in r09-F2-009
SHIFT = {1: 2, -1: 3, 2: 0, -2: 2, -4: 3}
KG = {1: 's', 2: 'z', 3: 'sdg'}


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
    assert np.abs(A @ c - th).max() < 1e-9, np.abs(A @ c - th).max()
    return {frozenset(S): ci for S, ci in zip(sup, c)}


def schedule(terms, wire):
    """exact content tracking of the window: returns the event list and the closing free ends."""
    base = dict(PR={'r'}, PT={'t'}, PL={'l'}, L={'v'}, a={'w23'})
    val = {k: set(v) for k, v in base.items()}
    cont = set()
    for w in START:
        cont ^= base[w]
    seq, visited = [], set()
    if frozenset(cont) in terms:
        seq.append(('rz', frozenset(cont)))
        visited.add(frozenset(cont))
    ntogY = 0
    for mv in PATH:
        if mv[0] == 'tog':
            if mv[1] == 'X':
                val['PR'] ^= {'w01'}
                seq.append(('togX',))
            else:
                ntogY += 1           # fused outside the window (a holds w23 for the whole window)
        else:
            cont ^= val[mv[1]]
            seq.append(('cx', wire[mv[1]]))
            fc = frozenset(cont)
            if fc in terms and fc not in visited:
                seq.append(('rz', fc))
                visited.add(fc)
    assert ntogY == 2 and PATH[1] == ('tog', 'Y') and PATH[-2] == ('tog', 'Y')
    assert visited == set(terms)
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
    rccx_e(b, F, g, a, 0, 1, True)          # a: c1 -> 0
    rccx_e(b, q2(2), q2(3), a)              # a: 0 -> w23 (fused: H H and the adjacent T phases cancel)
    b.h(F)
    zp = 0      # pending Z on f from the k = 2 shifts: Z_f CX(q -> f) = CX(q -> f) Z_q Z_f
    for ev in seq:
        if ev[0] == 'cx':
            b.cx(ev[1], F)
            if zp:
                b.z(ev[1])
        elif ev[0] == 'togX':
            rccx_e(b, q2(0), q2(1), PR)     # PR: p_r <-> p_r ^ w01 (self-inverse word; phases cancel in pairs)
        else:
            c = terms[ev[1]]
            k = SHIFT[int(round(c / spec.beta))]
            b.rz(c - k * np.pi / 2, F)
            if k == 2:
                zp ^= 1
            elif k:
                if zp:          # pending Z_f . S^k = S^(k+2): the Z is absorbed into the odd shift's phase gate
                    getattr(b, KG[(k + 2) % 4])(F)
                    zp = 0
                else:
                    getattr(b, KG[k])(F)
    if zp:
        b.z(F)
    b.h(F)
    rccx_e(b, q2(2), q2(3), a, inv=True)
    rccx_e(b, F, g, a, 0, 1)
    encode(b)
    leg_tail(b, g, a, X1, zg1)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
