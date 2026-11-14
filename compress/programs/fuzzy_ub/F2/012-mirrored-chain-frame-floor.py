"""SUMMARY: new frame/line variant of r10-F2-010 (does NOT beat it; recorded as the best valid new-datapath attempt of round 12): mirrored g chain L: 0 -> c13 = ~p_t&~s_l [(1 3) 7-T Fredkin] -> g = ~p_t&(s_r^s_l) by the toggle ~s_r&~p_t, a = ~f&~g with the complemented (0 2) control (X on the line around the Fredkin; control polarity is free because an uncontrolled swap is a wire relabel), CZ(g, f) = Z(f) Z(a) Z(L) as the free walk end, so sectors 1 and 4 exchange their W/V roles; Bell decoders (0,1),(2,3), w23 fused onto a, w01 toggled onto p_r inside the H(f) window, 9-term R_x support (t, rt, tlv, rtlv, rtW, rtlW, rtlV, tlvV, rtlWV; same 4 x beta, 4 x 2 beta, 1 x 4 beta multiset and the parent's per-class k pi/2 shifts, no new angle tuning) walked in 10 CX from the free start {r, t, l, g} to the free end {r, t}; 84 CX, T_eps 638, depth_CT 1538, 10 qubits.
DISCOVERY: negative (exhaustive): for the (0 2)(1 3) word with decoder (0,1),(2,3), two lines each made by one rccx of wire literals (f, s_k, p_k, p_r^p_l, negations; the second may read the first only after its f-removing rccx) and each Fredkin control free up to complement give exactly 8 control designs: 4 g-line chains (best walks 9 = r10-F2-010, 10 = this program, > 11 for the other two with W toggled and V fused) and 4 q-line chains (q = p_t&~(p_r^p_l), sectors 3 and 6 on the other f-controlled swap, one Fredkin under an AND with ~(p_r^p_l), which needs the p_r^p_l wire) whose walks need >= 11 CX even if q were a free end (12 to 13 with the free ends that exist); the parent is the unique 83-CX point of this space.
DISCOVERY: negative: nine qubits (second Fredkin control toggled onto a parity wire as p_t ^ AND) are valid only for W/V role assignments whose best walk is >= 14 CX (>= 88 CX in total); for the four role assignments with 9- or 10-CX walks the required AND (s_t&~g onto p_t, or ~f&~g) either reads the target wire itself or needs its own line.
DISCOVERY: depth floor of r10-F2-010 without new angle tuning: 1521 = 43 (head chain + H) + 1423 (nine serial gridsynth words) + 9 walk CX (one 2-step) + 3 S^k gates of the odd-k terms (only f ever holds their parities, so they are serial on f wherever they sit) + 1 H + 42 (tail chain); reordering the walk only moves the last S^k into the middle at equal total.
"""
FAMILY = "F2"
PARENT = "r10-F2-010"
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


def cswap_neg(b, i, j, ctrl, rev=False, zc=0):
    """Fredkin with the complemented control 1 ^ ctrl (X on the control line around the 7-CX word)."""
    b.x(ctrl)
    cswap(b, i, j, ctrl, rev, zc)
    b.x(ctrl)


def leg_head(b, L, a, X0, zg):
    """mirrored g chain: L: 0 -> c13 = ~p_t&~s_l, swap(q2^1,q2^3)[c13], L: c13 -> g = ~p_t&(s_r^s_l) (toggle ~s_r&~p_t),
    a: 0 -> ~f&~g, swap(q2^0,q2^2)[1 ^ a] (complemented control).  zg: CZ(g, f) = Z(f) Z(a) Z(L) while a holds ~f&~g and
    L holds g ((-1)^(~f~g) = (-1)^(~g) (-1)^f (-1)^(fg))."""
    if zg:
        b.z(F)
    cx_par(b, PT, PT in X0)
    rccx_e(b, PT, PL, L, 1, 1, zfix=False)   # reads raw s_l; its Z fix joins the Fredkin
    cx_par(b, PL, PL in X0)                  # raw s_l is not read again
    cswap(b, 1, 3, L, zc=1)
    rccx_e(b, PR, PT, L, 1, 1, zfix=not zg)  # L: c13 -> g (reads raw s_r); Z fix and the Z(L) of CZ(g, f) cancel if zg
    rccx_e(b, L, F, a, 1, 1, zfix=False)     # a = ~g & ~f on a clean target; its Z fix joins the Fredkin
    cx_par(b, PR, PR in X0)
    cswap_neg(b, 0, 2, a, zc=1 ^ zg)


def leg_tail(b, L, a, X1, zg):
    """exact inverse of leg_head (with the closing CZ(g, f) = Z(f) Z(a) Z(L) if zg)."""
    cswap_neg(b, 0, 2, a, True, zc=1 ^ zg)
    cz_par(b, PR, PR in X1)
    rccx_e(b, L, F, a, 1, 1, True, zfix=False)
    rccx_e(b, PR, PT, L, 1, 1, True, zfix=not zg)
    cswap(b, 1, 3, L, True, zc=1)
    cz_par(b, PL, PL in X1)
    rccx_e(b, PT, PL, L, 1, 1, True, zfix=False)
    cz_par(b, PT, PT in X1)
    if zg:
        b.z(F)


def decode(b):
    for (i, j) in [(0, 1), (2, 3)]:
        b.cx(q2(i), q2(j)); b.h(q2(i))


def encode(b):
    for (i, j) in [(2, 3), (0, 1)]:
        b.h(q2(i)); b.cx(q2(i), q2(j))


# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V for this frame (sectors 1 and 4 carry W resp. V instead of V resp. W)
LAM = {0: (0, -1, 0, 1), 1: (0, 1, 0, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 0, 1, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
SUPPORT = [['t'], ['r', 't'], ['t', 'l', 'v'], ['r', 't', 'l', 'v'], ['r', 't', 'w01'], ['r', 't', 'l', 'w01'],
           ['r', 't', 'l', 'w23'], ['t', 'l', 'v', 'w23'], ['r', 't', 'l', 'w01', 'w23']]
PATH = [('tog', 'Y'), ('cx', 'PR'), ('cx', 'a'), ('cx', 'L'), ('cx', 'PR'), ('cx', 'PR'), ('tog', 'X'), ('cx', 'PR'),
        ('cx', 'a'), ('cx', 'PL'), ('cx', 'PR'), ('tog', 'X'), ('cx', 'PR'), ('tog', 'Y')]
START = ['PR', 'PT', 'PL', 'L']   # opening f content {r, t, l, v}
SHIFT = {1: 2, -1: 3, 2: 0, -2: 2, -4: 3}   # parent's per-class k (rz(theta) = rz(theta - k pi/2) S^k), unchanged
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
    assert ntogY == 2 and PATH[0] == ('tog', 'Y') and PATH[-1] == ('tog', 'Y')
    assert visited == set(terms), (visited ^ set(terms))
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
    rccx_e(b, F, g, a, 1, 1, True)          # a: ~f&~g -> 0
    rccx_e(b, q2(2), q2(3), a)              # a: 0 -> w23 (fused: H H and the adjacent T phases cancel)
    b.h(F)
    zp = 0
    for ev in seq:
        if ev[0] == 'cx':
            b.cx(ev[1], F)
            if zp:
                b.z(ev[1])
        elif ev[0] == 'togX':
            rccx_e(b, q2(0), q2(1), PR)     # PR: p_r <-> p_r ^ w01 (self-inverse word)
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
    rccx_e(b, q2(2), q2(3), a, inv=True)
    rccx_e(b, F, g, a, 1, 1)
    encode(b)
    leg_tail(b, g, a, X1, zg1)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
