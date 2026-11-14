"""SUMMARY: no construction beats (83, 638, 1517, 10) (CX and T floors of the two-line family re-derived below), so this is a T-lean Pareto point: the r11-F2-011 seven-rotation datapath (parity frame; L: 0 -> ~p_t&~s_r -> g; a: 0 -> c1 = f&~g -> p_r&~g (rccx with the raw s_r wire) -> h = [p=3]; w01 toggled onto p_r and w23 onto a inside the H(f) window; 7-term 9-CX R_x walk, archived per-class k pi/2 shifts, no new angle choices) on the r12-F1-012 diagonal q2 frame (Bell(02)(13) decoder E1, the two Fredkins as CCZ(L, P13), CCZ(a, P02) fused with one in-pair CX, 4-CX recoupling E2 to AND-decoded (01)/(23) pairs, Z fixes as phase flips on fresh rccx targets); cx(f -> p_r) moves after the a conversion; (89, 514, 1246 -> 1242, 10).
DISCOVERY: the F1-012 CCZ frame and the F2-011 h-line chain compose unchanged (valid at all three angle pairs on the first try, 1246 -> 1242 depth_CT); a CX-neutral T gain at 83 CX is blocked because every route to h needs 2 extra AND toggles: c1 ^ h = s_r&~g ^ p_r&p_l is not x&(y^z) for wire literals (no 4-CX shared-control fusion), h ^ g has 3 true points over (p_r, p_t, p_l) so L: g -> h is not an XOR of two literal ANDs, and with a = h^w23 fused outside the window one inner toggle reaches h or V terms but not both.
DISCOVERY: [p=3] = p_r & (g ^ ~p_l) exactly, so h onto a fresh line is a 4-CX pair of rccx sharing the twice-used control p_r (AND(p_r, L) ^ AND(p_r, ~p_l)), 8 CX round trip; on the 83-CX datapath (a: c1 -> 0 -> w23 kept) a fresh h line gives 7 rotations at >= 91 CX (worse than 89), and k0 over (r, l, v) with y = g^~p_l on a wire still has 4 Walsh terms (the 32-function coset bound holds).
DISCOVERY: corner picture of the sectors (checked against the oracle): the q2 spin of link l sits at its head corner if q1 = 0 and at its tail corner if q1 = 1, so p6 is occupation (1111), p3 (2020), the rest (2110); the f=0 singlet pair is (12) for p0,p4, (01) for p1,p5,p7, (23) for p2, (01)(23) for p3, the f=1 pair (03) for p0-p3, (23) for p4,p5, (12) for p7, (03)(12) for p3, so the pairing ((01)(23) vs (03)(12)) changes between the f sides iff t|(r^l), and the per-side pairing indicator n(f,p) = ~f~r~t ^ f(~l|t) (p6 assigned either way) has ANF degree 3 in (f, p) and in the raw q1 bits: any frame that carries the pairing decision on one control (K4 two-swap words, S3 words X^a Y^b and X^a Y^b X^c, where it is one control or the XOR of two) needs a degree-3 line, i.e. 2 ANDs.
"""
FAMILY = "F3"
PARENT = "r11-F2-011"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7


def q2(i):
    return 2 * i



INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's', 'h': 'h', 'x': 'x', 'z': 'z', 'cx': 'cx'}


def rccx_e(b, c0, c1, t, n0=0, n1=0, inv=False, zfix=True, flip=0):
    """qiskit rccx(c0', c1', t) with c0' = c0 xor n0, c1' = c1 xor n1, as an explicit 3-CX word: the negations are
    T <-> Tdg swaps on the parities that contain the negated control (+ one Z on t for n0), no X gates."""
    T = lambda f: 'tdg' if f ^ flip else 't'
    Td = lambda f: 't' if f ^ flip else 'tdg'
    w = [('h', t), (T(0), t), ('cx', c1, t), (Td(n1), t), ('cx', c0, t), (T(n0 ^ n1), t), ('cx', c1, t), (Td(n0), t), ('h', t)]
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



# ---------------------------------------------------------------------------------------------------------------
# diagonal leg frame: Bell(02)(13) decoder E1, the two Fredkins as CCZ phases (each fused with one in-pair CX map),
# a 4-CX recoupling E2 to a frame where the (01)- and (23)-singlet projectors are ANDs of two wires
# ---------------------------------------------------------------------------------------------------------------
LOCN = {'': [], 'h': ['h'], 's': ['s'], 'hs': ['h', 's'], 'sh': ['s', 'h'], 'hsh': ['h', 's', 'h']}
E1_PRE = ['', '', 'sh', 'sh']           # local word per logical q2 wire (time order), then CX(2->0), CX(3->1)
E1_CX = [(2, 0), (3, 1)]
E1_POST = ['hsh', 'hsh', 'hsh', 'hsh']
# CCZ(c, x, y) followed by CX(y -> x): 5 CX, the control line is a CX target once (holds c^y for one phase)
CCZ_NET = [('cx', 0, 1), ('cx', 2, 0), ('cx', 2, 1), ('cx', 2, 0), ('cx', 0, 1)]
E2_STEPS = [(1, '', 0, ''), (2, '', 3, ''), (0, 'h', 2, ''), (1, 'h', 3, '')]   # (c, local_c, t, local_t), CX(c->t)


def ccz_block(c, x, y):
    """CCZ(c, x, y) then CX(y -> x), as a list of gates on the physical wires (c, x, y)."""
    w = [c, x, y]
    cont = [1, 2, 4]
    out = [('t', c), ('t', x), ('t', y)]
    done = set()
    for _, i, j in CCZ_NET:
        out.append(('cx', w[i], w[j]))
        cont[j] ^= cont[i]
        v = cont[j]
        if v not in (1, 2, 4) and v not in done:
            done.add(v)
            out.append(('tdg' if bin(v).count('1') == 2 else 't', w[j]))
    assert done == {3, 5, 6, 7} and cont == [1, 6, 4], (done, cont)
    return out


def inv_list(gl):
    return [(INV[g[0]],) + tuple(g[1:]) for g in reversed(gl)]


def emit(b, gl):
    for g in gl:
        getattr(b, g[0])(*g[1:])


def q2_frame(L, a):
    """physical gate lists of the four q2 blocks and the wires of the W (w01) and V (w23) AND pairs."""
    phys = [q2(i) for i in range(4)]
    e1 = []
    for i in range(4):
        e1 += [(g, phys[i]) for g in LOCN[E1_PRE[i]]]
    for i, j in E1_CX:
        e1.append(('cx', phys[i], phys[j]))
    for i in range(4):
        e1 += [(g, phys[i]) for g in LOCN[E1_POST[i]]]
    cL = ccz_block(L, phys[1], phys[3])          # in-pair map (y -> x) then relabel l1 <-> l3
    phys[1], phys[3] = phys[3], phys[1]
    ca = ccz_block(a, phys[0], phys[2])
    phys[0], phys[2] = phys[2], phys[0]
    e2 = []
    for c, lc, t, lt in E2_STEPS:
        e2 += [(g, phys[c]) for g in LOCN[lc]] + [(g, phys[t]) for g in LOCN[lt]] + [('cx', phys[c], phys[t])]
    return e1, cL, ca, e2, phys


def _mat(gl, wires):
    """unitary of a gate list on the given physical wires (bit k of the index = wires[k])."""
    n = len(wires)
    pos = {w: k for k, w in enumerate(wires)}
    U = np.eye(2 ** n, dtype=complex)
    one = {'h': np.array([[1, 1], [1, -1]]) / np.sqrt(2), 's': np.diag([1, 1j]), 'sdg': np.diag([1, -1j]),
           't': np.diag([1, np.exp(1j * np.pi / 4)]), 'tdg': np.diag([1, np.exp(-1j * np.pi / 4)]),
           'x': np.array([[0, 1], [1, 0]]), 'z': np.diag([1, -1])}
    idx = np.arange(2 ** n)
    for g in gl:
        if g[0] == 'cx':
            c, t = pos[g[1]], pos[g[2]]
            perm = idx ^ (((idx >> c) & 1) << t)
            G = np.zeros((2 ** n, 2 ** n))
            G[perm, idx] = 1
        else:
            q = pos[g[1]]
            G = np.array([[1]])
            for k in range(n - 1, -1, -1):
                G = np.kron(G, one[g[0]] if k == q else np.eye(2))
        U = G @ U
    return U


def frame_fix(L, a):
    """emission-time check of the diagonal frame against the parent's Fredkin frame and choice of the X fixes
    (after E1: the CCZ pairs see the singlet as |11>; after E2: the W / V pairs see the singlet as |11>)."""
    e1, cL, ca, e2, phys = q2_frame(L, a)
    wires = [q2(i) for i in range(4)] + [L, a]
    # parent frame on q2 for line values (vL, va): Dec01,23 . SW02^va . SW13^vL
    def par(vL, va):
        gl = []
        if vL:
            gl += [('cx', q2(1), q2(3)), ('cx', q2(3), q2(1)), ('cx', q2(1), q2(3))]
        if va:
            gl += [('cx', q2(0), q2(2)), ('cx', q2(2), q2(0)), ('cx', q2(0), q2(2))]
        gl += [('cx', q2(0), q2(1)), ('h', q2(0)), ('cx', q2(2), q2(3)), ('h', q2(2))]
        return _mat(gl, wires)
    best = None
    for fx in itertools.product(range(2), repeat=4):
        x1 = [('x', q2(i)) for i in range(4) if fx[i]]
        U0 = _mat(e1 + x1 + cL + ca + e2, wires)
        blocks = {}
        ok = True
        for vL, va in itertools.product(range(2), repeat=2):
            s = vL << 4 | va << 5
            sel = [k for k in range(64) if (k >> 4) == (s >> 4)]
            Uq = U0[np.ix_(sel, sel)]
            Pq = par(vL, va)[np.ix_(sel, sel)]
            blocks[(vL, va)] = Uq @ Pq.conj().T
        Q = blocks[(0, 0)]
        if all(np.abs(B - Q).max() < 1e-9 for B in blocks.values()):
            best = (fx, Q)
            break
    assert best is not None, 'diagonal frame does not reproduce the Fredkin frame'
    fx, Q = best
    # W = singlet(01) projector in the parent decoded frame = |11><11| on q2^0, q2^1; V on q2^2, q2^3
    def proj(i, j, vi, vj):
        d = np.array([1.0 if ((k >> i) & 1) == vi and ((k >> j) & 1) == vj else 0.0 for k in range(16)])
        return np.diag(d)
    P01, P23 = proj(0, 1, 1, 1), proj(2, 3, 1, 1)
    q2w = [q2(i) for i in range(4)]
    names = list(LOCN)
    for fin in itertools.product(range(len(names)), repeat=4):
        lf = []
        for i in range(4):
            lf += [(g, q2(i)) for g in LOCN[names[fin[i]]]]
        Qf = _mat(lf, q2w) @ Q
        out = []
        for Pp in (P01, P23):
            Pw = Qf @ Pp @ Qf.conj().T
            if np.abs(Pw.imag).max() > 1e-9 or np.abs(Pw - np.diag(np.diag(Pw))).max() > 1e-9:
                break
            hit = None
            for (u, v) in itertools.combinations(range(4), 2):
                for vu, vv in itertools.product(range(2), repeat=2):
                    if np.abs(Pw - proj(u, v, vu, vv)).max() < 1e-9:
                        hit = (u, v, vu, vv)
            if hit is None:
                break
            out.append(hit)
        if len(out) == 2:
            break
    assert len(out) == 2, 'W/V projectors are not ANDs of two wires'
    x2 = []
    pairs = []
    for (u, v, vu, vv) in out:
        if not vu:
            x2.append(('x', q2(u)))
        if not vv:
            x2.append(('x', q2(v)))
        pairs.append((q2(u), q2(v)))
    x1 = [('x', q2(i)) for i in range(4) if fx[i]]
    return e1 + x1, cL, ca, e2 + lf + x2, pairs



def leg_head(b, L, a, X0, zg, FR):
    """Bell(02)(13) frame E1; L: 0 -> c2 = ~p_t&~s_r, CCZ(c2, P13) [= swap(q2^1,q2^3)[c2]], L: c2 -> g,
    a: 0 -> c1 = f&~g, CCZ(c1, P02) [= swap(q2^0,q2^2)[c1]], then a: c1 -> p_r&~g (rccx with the raw s_r wire, f not
    read) -> h = [p = 3] (rccx(p_r, p_l), fused).  zg: CZ(g, f) = Z(f) Z(a) while a holds c1."""
    e1, cL, ca, e2, pairs = FR
    emit(b, e1)
    if zg:
        b.z(F)
    cx_par(b, PT, PT in X0)
    rccx_e(b, PT, PR, L, 1, 1, zfix=False, flip=1)     # fresh target: all four phases flipped = its Z fix
    emit(b, cL)
    rccx_e(b, PL, PT, L, 1, 1)
    rccx_e(b, L, F, a, 1, 0, zfix=False, flip=1 ^ zg)  # Z fix of the negated c0 and the CZ(g, f) Z(a)
    cx_par(b, PL, PL in X0)
    emit(b, ca)
    rccx_e(b, PR, L, a, 0, 1)                          # a: c1 -> p_r & ~g   (PR still holds raw s_r)
    cx_par(b, PR, PR in X0)
    rccx_e(b, PR, PL, a)                               # a: p_r~g -> h = p_r p_t ~p_l


def inverse(ops):
    out = []
    for n, p, qs in reversed(ops):
        assert n != 'rz'
        out.append((INV[n], p, qs))
    return out

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
    FR = frame_fix(g, a)
    (W0, W1), (V0, V1) = FR[4]
    terms = fit_terms(spec.beta)
    seq, end = schedule(terms, wire)
    X0 = frozenset(wire[w] for w in START if w != 'L')
    X1 = frozenset(wire[w] for w in end if w != 'L')
    zg0, zg1 = 'L' in START, 'L' in end
    leg_head(b, g, a, X0, zg0, FR)
    emit(b, FR[3])
    b.h(F)
    zp = 0
    for ev in seq:
        if ev[0] == 'cx':
            b.cx(ev[1], F)
            if zp:
                b.z(ev[1])
        elif ev[0] == 'togX':
            rccx_e(b, W0, W1, PR)     # PR: p_r <-> p_r ^ w01 (self-inverse word; phases cancel in pairs)
        elif ev[0] == 'togY':
            rccx_e(b, V0, V1, a)      # a: h <-> h ^ w23 (self-inverse word; a is only a control in between)
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
    emit(b, inv_list(FR[3]))
    t = Rec()
    leg_head(t, g, a, X1, zg1, FR)
    b.ops += inverse(t.ops)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
