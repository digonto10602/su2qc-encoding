"""SUMMARY: r12-F1-012 datapath unchanged except the recoupling after the two CCZ blocks (parity frame; L: 0 -> ~p_t&~s_r -> g; a = f&~g; Bell(02)(13) decoder E1, CCZ(L, P13), CCZ(a, P02) with fused in-pair CX; w23 fused onto a, w01 toggled onto the p_r wire; 9-term 9-CX R_x walk, same per-class k pi/2 shifts, no new angle tuning): the 4-CX recoupling E2 is replaced by a 2-CX partial recoupling E2' (two generalised CX on the disjoint wire pairs (0,1), (2,3), control basis X, target basis Y, found by Pauli tracking of the four singlet stabilizers), after which each singlet projector is an AND of one wire bit and a two-wire parity; both singlet toggles become 4-CX rccx words whose once-used control is that parity (one CX per wire, negations as T <-> Tdg swaps), chosen and checked at emission time against the Fredkin frame; E2' saves 2 x 2 CX, the four parity toggles cost 4 x 1 CX more: (83, 638, 1517, 10), a tie with r12-F1-012 (does not beat it).
DISCOVERY: negative (exhaustive Pauli tracking): after the F1-012 CCZ blocks the singlet stabilizers are X1X0, X3X2Z1Z0 (pair 01) and Z3Z2X1X0, X3X2 (pair 23), no pair is wire-local; over all recouplings of <= 3 generalised CX (control basis -> Z, target basis -> X, 108 per step), also split into one block before the w23 toggle and one before the window, and also from the unfused CCZ frame, with toggles that are rccx words on parity controls (cost 2|twice-used| + |once-used|), the minimum of 2k + 2(c01 + c23) is 20 CX (k = 2 with 4 + 4, k = 3 with 3 + 4, F1-012 k = 4 with 3 + 3), so the q2 frame plus singlet toggles is 44 CX in every Bell(02)(13) variant, the same as the Fredkin + (01)(23) decoder leg.
DISCOVERY: negative: for each parity sector the permutation pairs (s0, s1) in S4 x S4 with s1 D_p s0^-1 in span{1, S01, S23, S01 S23} number 32 (p3 64, p6 96) and also give indicator normal forms (2 w23, 2 w01, k0 != 0) and lambda6 in {1, W, V, WV}; their relative elements s1 s0^-1 (4 to 20 per sector) and s0^-1 s1 (4 to 10) have empty intersection over the 8 sectors, so no leg made of an f-independent sector permutation Q(p) plus one fixed f-controlled permutation (control f alone, no f-dependent line) exists.
DISCOVERY: negative: parity controls do not shorten the T-lean h line: a single toggle a: c1 -> c1 ^ AND(X, Y) with X, Y affine in the wires is f-free only for (X, Y) = (f ^ alpha, ~g) or (f ^ alpha, f ^ alpha ^ g), leaving alpha ~g with alpha in span{1, r, t, l, g}, and none of these functions lies in [p=3] + span{1, r, t, l, g}; depth_CT 1517 = 40 (head line chain) + 1437 (H, nine words 1423, 9 walk CX with one 2-step, 3 S^k, H) + 40 (tail), E2 / E2' lie off the critical path.
"""
FAMILY = "F2"
PARENT = "r12-F1-012"
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


# ---------------------------------------------------------------------------------------------------------------
# partial recoupling: after the two CCZ blocks the (01) / (23) singlet stabilizers are X1X0, X3X2Z1Z0 and Z3Z2X1X0, X3X2
# (no wire-local Z frame); two generalised CX (control basis -> Z, target basis -> X) on the disjoint wire pairs (0,1),
# (2,3) make each singlet projector an AND of a one-wire bit and a two-wire parity, toggled by a 4-CX rccx whose
# once-used control is the parity (CX from both wires).  E2' = 2 CX instead of 4 per leg, each toggle 4 CX instead of 3.
# ---------------------------------------------------------------------------------------------------------------
E2P = [(0, 'X', 1, 'Y'), (2, 'X', 3, 'Y')]     # (c, basis on c, t, basis on t): generalised CX(c -> t), logical q2 wires
_PAULI = {'X': np.array([[0, 1], [1, 0]]), 'Y': np.array([[0, -1j], [1j, 0]]), 'Z': np.diag([1, -1])}


def _locword(src, dst):
    """a LOCN word whose unitary maps the Pauli src to +-dst by conjugation."""
    for w in LOCN:
        U = _mat([(g, 0) for g in LOCN[w]], [0])
        M = U @ _PAULI[src] @ U.conj().T
        if np.abs(np.abs(np.trace(M @ _PAULI[dst])) / 2 - 1) < 1e-9:
            return LOCN[w]
    raise AssertionError((src, dst))


def frame_fix2(L, a):
    """F1-012 frame (E1, X fixes, CCZ(L, P13), CCZ(a, P02)) checked against the Fredkin frame, then the 2-CX partial
    recoupling E2' and the parity-AND description of both singlet projectors (emission-time search over final
    wire-local Cliffords); returns (E1+X, CCZ_L, CCZ_a, E2'+locals, [W spec, V spec]) with spec = (C1, C0, n1, n0):
    toggle = rccx with twice-used control parity C1 (xor n1) and once-used control parity C0 (xor n0)."""
    e1, cL, ca, _, _ = q2_frame(L, a)
    wires = [q2(i) for i in range(4)] + [L, a]
    q2w = [q2(i) for i in range(4)]

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
        U0 = _mat(e1 + x1 + cL + ca, wires)
        blocks = []
        for vL, va in itertools.product(range(2), repeat=2):
            sel = [k for k in range(64) if (k >> 4) == (vL | va << 1)]
            blocks.append(U0[np.ix_(sel, sel)] @ par(vL, va)[np.ix_(sel, sel)].conj().T)
        if all(np.abs(B - blocks[0]).max() < 1e-9 for B in blocks):
            best = (x1, blocks[0])
            break
    assert best is not None, 'diagonal frame does not reproduce the Fredkin frame'
    x1, Q = best
    e2 = []
    for c, bc, t, bt in E2P:
        e2 += [(g, q2(c)) for g in _locword(bc, 'Z')] + [(g, q2(t)) for g in _locword(bt, 'X')]
        e2.append(('cx', q2(c), q2(t)))
    U = _mat(e2, q2w) @ Q
    d11 = lambda i, j: np.diag([1.0 if (k >> i) & (k >> j) & 1 else 0.0 for k in range(16)])
    P01, P23 = d11(0, 1), d11(2, 3)
    names = list(LOCN)
    pick = None
    for fin in itertools.product(range(len(names)), repeat=4):
        lf = []
        for i in range(4):
            lf += [(g, q2(i)) for g in LOCN[names[fin[i]]]]
        Qf = _mat(lf, q2w) @ U
        specs, cost = [], 0
        for Pp in (P01, P23):
            Pw = Qf @ Pp @ Qf.conj().T
            if np.abs(Pw.imag).max() > 1e-9 or np.abs(Pw - np.diag(np.diag(Pw))).max() > 1e-9:
                break
            S = [k for k in range(16) if Pw[k, k].real > 0.5]
            z0 = S[0]
            span = {s ^ z0 for s in S}
            cons = [u for u in range(1, 16) if all(bin(u & s).count('1') % 2 == 0 for s in span)]
            if len(S) != 4 or len(cons) != 3:
                break
            opts = []
            for u, v in itertools.permutations(cons, 2):
                opts.append((2 * bin(u).count('1') + bin(v).count('1'), u, v))
            cst, u, v = min(opts)
            au, av = bin(u & z0).count('1') % 2, bin(v & z0).count('1') % 2
            assert np.abs(np.diag([1.0 if (bin(u & k).count('1') % 2 == au and bin(v & k).count('1') % 2 == av)
                                   else 0.0 for k in range(16)]) - Pw).max() < 1e-9
            specs.append(([q2(i) for i in range(4) if (u >> i) & 1], [q2(i) for i in range(4) if (v >> i) & 1], 1 ^ au, 1 ^ av))
            cost += cst
        if len(specs) == 2 and (pick is None or cost < pick[0]):
            pick = (cost, lf, specs)
    assert pick is not None, 'W/V projectors are not parity ANDs'
    cost, lf, specs = pick
    assert cost == 8, cost
    return e1 + x1, cL, ca, e2 + lf, specs


def rccx_p(b, C0, C1, t, n0=0, n1=0, inv=False, zfix=True):
    """rccx_e with parity controls: c0 = xor of the wires C0 (xor n0, read once), c1 = xor of C1 (xor n1, read twice);
    the phase polynomial is the same (contents t, t+c1, t+c0+c1, t+c0), each control CX becomes one CX per wire."""
    T = lambda f: 'tdg' if f else 't'
    Td = lambda f: 't' if f else 'tdg'
    w = [('h', t), ('t', t)] + [('cx', c, t) for c in C1] + [(Td(n1), t)] + [('cx', c, t) for c in C0] + \
        [(T(n0 ^ n1), t)] + [('cx', c, t) for c in C1] + [(Td(n0), t), ('h', t)]
    if n0 and zfix:
        w.append(('z', t))
    if inv:
        w = [(INV[g[0]],) + g[1:] for g in reversed(w)]
    for g in w:
        getattr(b, g[0])(*g[1:])


def leg_head(b, L, a, X0, zg, FR):
    """L: 0 -> c2 = ~p_t&~s_r, CCZ(c2, P13) [= swap(q2^1,q2^3)[c2] in the Bell(02)(13) frame], L: c2 -> g, a: 0 -> c1 =
    f&~g, CCZ(c1, P02) [= swap(q2^0,q2^2)[c1]].  zg: CZ(g, f) = Z(f) Z(a) while a holds c1 (the walk's opening g toggle)."""
    e1, cL, ca, e2, pairs = FR
    emit(b, e1)
    if zg:
        b.z(F)
    cx_par(b, PT, PT in X0)
    rccx_e(b, PT, PR, L, 1, 1, zfix=False, flip=1)    # fresh target: all four phases flipped = its Z fix
    cx_par(b, PR, PR in X0)
    emit(b, cL)
    rccx_e(b, PL, PT, L, 1, 1)
    rccx_e(b, L, F, a, 1, 0, zfix=False, flip=1 ^ zg)  # Z fix of the negated c0, cancelled by CZ(g, f) = Z(f) Z(a)
    cx_par(b, PL, PL in X0)
    emit(b, ca)


def leg_tail(b, L, a, X1, zg, FR):
    """exact inverse of leg_head (with the closing CZ(g, f) = Z(f) Z(a) if zg)."""
    e1, cL, ca, e2, pairs = FR
    emit(b, inv_list(ca))
    cz_par(b, PL, PL in X1)
    rccx_e(b, L, F, a, 1, 0, True, zfix=False, flip=1 ^ zg)
    rccx_e(b, PL, PT, L, 1, 1, True)
    emit(b, inv_list(cL))
    cz_par(b, PR, PR in X1)
    rccx_e(b, PT, PR, L, 1, 1, True, zfix=False, flip=1)
    cz_par(b, PT, PT in X1)
    if zg:
        b.z(F)
    emit(b, inv_list(e1))


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
    FR = frame_fix2(g, a)
    WS, VS = FR[4]
    terms = fit_terms(spec.beta)
    seq, end = schedule(terms, wire)
    X0 = frozenset(wire[w] for w in START if w != 'L')
    X1 = frozenset(wire[w] for w in end if w != 'L')
    zg0, zg1 = 'L' in START, 'L' in end
    leg_head(b, g, a, X0, zg0, FR)
    emit(b, FR[3])
    rccx_e(b, F, g, a, 0, 1, True)          # a: c1 -> 0
    rccx_p(b, VS[1], VS[0], a, VS[3], VS[2])   # a: 0 -> w23 (fused: H H and the adjacent T phases cancel)
    b.h(F)
    zp = 0      # pending Z on f from the k = 2 shifts: Z_f CX(q -> f) = CX(q -> f) Z_q Z_f
    for ev in seq:
        if ev[0] == 'cx':
            b.cx(ev[1], F)
            if zp:
                b.z(ev[1])
        elif ev[0] == 'togX':
            rccx_p(b, WS[1], WS[0], PR, WS[3], WS[2])   # PR: p_r <-> p_r ^ w01 (self-inverse word)
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
    rccx_p(b, VS[1], VS[0], a, VS[3], VS[2], inv=True)
    rccx_e(b, F, g, a, 0, 1)
    emit(b, inv_list(FR[3]))
    leg_tail(b, g, a, X1, zg1, FR)
    for n, p, qs in peephole(b.ops):
        getattr(B, n)(*p, *qs)
    B.free([a, g])
    return B
