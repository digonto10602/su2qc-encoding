"""SUMMARY: r08-F2-008 datapath (parity frame, L: 0 -> ~p_t&~s_r -> g, a = f&~g, two-swap frame, 9-term R_x walk on f with free ends {p_r, p_t, p_l, g}) with the F1-008 Pauli-scheduled q2 skeleton (7-T Fredkins) and the w23 ancilla removed: inside the H(f) window the w01 AND is toggled onto the p_r wire itself (rccx; p_r holds p_r^w01 between the two toggles, a palindromic phase-permutation of a control wire, so the rccx phases cancel) and w23 onto the a line right after c1 is cleared (fused with the c1 uncompute), and a Dijkstra over (visited terms, f content, toggle phase) gives the same 9-CX walk; negated rccx controls cost no X gates (T signs flipped), the CZ(g,f) free end is folded into the fresh a-compute, and f is the twice-used control of that compute, so depth_CT 1585 -> 1550; 83 CX, T_eps 638, 10 qubits.
DISCOVERY: AND toggles of the middle may target any walk control wire inside the H(f) window (w01 onto p_r, w23 onto the cleared a line) at the same 3 CX as a dedicated line; Dijkstra over (visited terms, f content, toggle phase) for the 16 minimal k0 supports, every pair of target lines in {a, new line, p_r, p_t, p_l, g} and every toggle order finds 9 CX as the minimum (8 nowhere), 9 CX with 10 qubits only for w01 on p_r and w23 on a (2 supports); one line carrying both ANDs is infeasible with 4 toggles (the W, V and WV terms need w-parts w01, w23 and w01^w23, and inside the w01^w23 phase of a single line the f content can only flip by w01^w23).
DISCOVERY: general CX networks inside the window (targets f, p_r, p_t, p_l, g or a; a rotation on any wire holding f~ + term) with the same toggles: a DFS with the one-new-term-per-CX bound finds no 9-CX network that splits the 9 rotations onto two wires for any minimal k0 support, so depth_CT stays bound by the 9 serial gridsynth words (1451 of the 1550 levels).
DISCOVERY: negated rccx controls are free: X on the twice-used control flips the signs of the two middle T phases, X on the once-used control flips two adjacent phases and leaves one Z on the target before the first or after the last H, which vanishes on a fresh/cleared line or cancels against the mirrored leg (L conversion); a Z right after a fresh rccx is all four phases flipped (so Z(a) of the CZ(g,f) free end costs nothing, it commutes through the SEG_B parity window), and rccx on a fresh or cleared target is symmetric in its controls.
"""
FAMILY = "F3"
PARENT = "r08-F2-008"
import itertools
import numpy as np
from su2plaq.compress.builder import Builder

F, PR, PT, PL = 1, 3, 5, 7
INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's', 'h': 'h', 'x': 'x', 'z': 'z', 'cx': 'cx', 'rz': 'rz'}

# F1-008 q2 skeleton of one leg (wires 0..3 = q2 of links b, r, t, l; 4 = line L, 5 = line a): SEG_A while L holds
# c2 = ~p_t&~s_r (Fredkin (1 3)), SEG_B while a holds c1 = f&~g (Fredkin (0 2)), SEG_C into the middle frame.
SEG_A = [('t', 4), ('cx', 0, 2), ('h', 0), ('t', 0), ('t', 2), ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 0), ('tdg', 0), ('cx', 1, 3), ('h', 1), ('t', 1), ('t', 3), ('cx', 1, 4), ('tdg', 4), ('cx', 3, 4), ('t', 4), ('cx', 1, 4), ('tdg', 4), ('cx', 3, 4), ('s', 0), ('h', 0), ('h', 2), ('s', 2), ('h', 2), ('h', 1)]
SEG_B = [('t', 5), ('h', 2), ('cx', 2, 5), ('tdg', 5), ('h', 0), ('cx', 0, 5), ('tdg', 5), ('cx', 2, 5), ('t', 5), ('cx', 0, 5), ('h', 2), ('h', 0)]
SEG_C = [('h', 3), ('cx', 1, 3), ('h', 1), ('tdg', 1), ('z', 1), ('cx', 0, 1), ('s', 0), ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 2), ('s', 2), ('h', 2), ('h', 3), ('s', 3), ('cx', 2, 3), ('h', 1), ('h', 2), ('sdg', 2), ('h', 2), ('cx', 1, 2), ('s', 3), ('h', 3), ('sdg', 1), ('h', 1), ('h', 2)]
# middle frame: singlet indicators w01, w23 are ANDs of these (q2 wire index, negated) literals
LITS = {'01': [(1, True), (0, True)], '23': [(3, False), (2, False)]}

# lambda(p, W, V) = k0 + k1 W + k2 V + k3 W V, W = (-1)^w01, V = (-1)^w23, p = p_r + 2 p_t + 4 p_l
LAM = {0: (0, -1, 0, 1), 1: (0, 0, 1, -1), 2: (0, 1, 0, -1), 3: (1, -1, -1, 1),
       4: (0, 1, 0, -1), 5: (0, 0, -1, 1), 6: (0, 0, 0, 1), 7: (0, 0, 1, -1)}
# Walsh support over r=p_r, t=p_t, l=p_l, v=g, w01, w23 (k0 support (rt, tv, rtl, tlv); no constant term)
SUPPORT = [['r', 't'], ['t', 'v'], ['r', 't', 'l'], ['t', 'l', 'v'], ['r', 't', 'l', 'w01'], ['r', 't', 'v', 'w01'],
           ['t', 'l', 'w23'], ['r', 't', 'l', 'w23'], ['r', 't', 'l', 'w01', 'w23']]
# window schedule: ('tog', 'X') toggles w01 into the p_r wire, ('tog', 'Y') toggles w23 into the a line;
# ('cx', w) is CX(w -> f); a rotation is placed whenever the f content first equals a support term
PATH = [('tog', 'X'), ('tog', 'Y'), ('cx', 'PL'), ('cx', 'PR'), ('cx', 'L'), ('cx', 'PL'), ('cx', 'a'), ('cx', 'PR'),
        ('tog', 'X'), ('cx', 'PR'), ('cx', 'a'), ('tog', 'Y'), ('cx', 'PL')]
START = ['PT', 'PL', 'L']    # opening f content {t, l, v}: CZ(k, f) merged into the leg's parity CX, CZ(g, f) = Z(a) Z(f)
XLINE, YLINE = 'PR', 'a'


def q2(i):
    return 2 * i


def inverse(ops):
    out = []
    for o in reversed(ops):
        out.append(('rz', -o[1], o[2]) if o[0] == 'rz' else (INV[o[0]],) + tuple(o[1:]))
    return out


def rccx(c0, n0, c1, n1, t, z='pre', zflip=False):
    """X^n0(c0) X^n1(c1) . rccx(c0, c1, t) . X^n0 X^n1 without X gates: n1 flips the two middle phases, n0 flips two
    adjacent phases and leaves Z(t) before the first H (z='pre'; z=None drops it: target |0> there) or after the last H
    (z='post'; z='droppost' drops it).  zflip: Z(t) after a fresh-target rccx = all four phases flipped."""
    s = [1, -1, 1, -1]
    zpre = zpost = False
    if n1:
        s[1], s[2] = -s[1], -s[2]
    if n0:
        if z in ('post', 'droppost'):
            s[2], s[3] = -s[2], -s[3]
            zpost = (z == 'post')
        else:
            s[0], s[1] = -s[0], -s[1]
            zpre = (z == 'pre')
    if zflip:
        s = [-x for x in s]
    ph = lambda k: ('t' if s[k] > 0 else 'tdg', t)
    ops = [('z', t)] if zpre else []
    ops += [('h', t), ph(0), ('cx', c1, t), ph(1), ('cx', c0, t), ph(2), ('cx', c1, t), ph(3), ('h', t)]
    if zpost:
        ops.append(('z', t))
    return ops


def rccx_pair(c1, n1, d0, d1, m1, c0, t):
    """rccx(c0, ~^n1 c1, t) then rccx(d0, ~^m1 d1, t) with the inner H.H and the adjacent phases fused."""
    s1, s2 = [1, -1, 1, -1], [1, -1, 1, -1]
    if n1:
        s1[1], s1[2] = -s1[1], -s1[2]
    if m1:
        s2[1], s2[2] = -s2[1], -s2[2]
    g = lambda x: 't' if x > 0 else 'tdg'
    ops = [('h', t), (g(s1[0]), t), ('cx', c1, t), (g(s1[1]), t), ('cx', c0, t), (g(s1[2]), t), ('cx', c1, t)]
    comb = s1[3] + s2[0]
    ops += [('s', t)] if comb == 2 else ([('sdg', t)] if comb == -2 else [])
    ops += [('cx', d1, t), (g(s2[1]), t), ('cx', d0, t), (g(s2[2]), t), ('cx', d1, t), (g(s2[3]), t), ('h', t)]
    return ops


def cxpar(k, cz):
    """parity CX(f -> k), followed by CZ(k, f) at no CX cost if cz."""
    return [('sdg', k), ('cx', F, k), ('s', k), ('s', F)] if cz else [('cx', F, k)]


def seg(S, L, a):
    wm = {0: 0, 1: 2, 2: 4, 3: 6, 4: L, 5: a}
    return [(o[0],) + tuple(wm[q] for q in o[1:]) for o in S]


def leg_head(L, a, X0, zA):
    ops = cxpar(PT, PT in X0)
    ops += rccx(PT, 1, PR, 1, L, z=None)              # L: 0 -> ~p_t & ~s_r            (fresh)
    ops += seg(SEG_A, L, a)                           # swap(q2^1, q2^3)[L]
    ops += rccx(PL, 1, PT, 1, L, z='droppost')        # L: c2 -> g  (its Z(L) cancels against the mirrored leg's)
    ops += cxpar(PL, PL in X0)
    ops += rccx(L, 1, F, 0, a, z=None, zflip=zA)      # a: 0 -> f & ~g (fresh; zA = the Z(a) of CZ(g, f))
    ops += seg(SEG_B, L, a)                           # swap(q2^0, q2^2)[a]
    ops += cxpar(PR, PR in X0)
    ops += seg(SEG_C, L, a)                           # into the middle frame
    return ops


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


def circuit_ops(beta, a, g):
    wire = dict(PR=PR, PT=PT, PL=PL, L=g, a=a)
    base = dict(PR={'r'}, PT={'t'}, PL={'l'}, L={'v'}, a=set())
    (u0, n0), (u1, n1) = LITS['01']
    (v0, m0), (v1, m1) = LITS['23']
    ands = dict(X=(XLINE, q2(u0), n0, q2(u1), n1, 'w01'), Y=(YLINE, q2(v0), m0, q2(v1), m1, 'w23'))
    terms = fit_terms(beta)
    X0 = frozenset(wire[w] for w in START if w in ('PR', 'PT', 'PL'))
    # walk schedule with exact content tracking
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
            ln, c0, nn0, c1, nn1, wn = ands[mv[1]]
            first = wn not in val[ln]
            val[ln] ^= {wn}
            seq.append(('tog', wire[ln], c0, nn0, c1, nn1, first))
        else:
            cont ^= val[mv[1]]
            seq.append(('cx', wire[mv[1]]))
            fc = frozenset(cont)
            if fc in terms and fc not in visited:
                seq.append(('rz', fc))
                visited.add(fc)
    assert visited == set(terms)
    assert all(val[k] == base[k] for k in val)
    end = [w for w in ('PR', 'PT', 'PL', 'L') if base[w] <= cont]
    e = set()
    for w in end:
        e ^= base[w]
    assert e == cont
    X1 = frozenset(wire[w] for w in end if w in ('PR', 'PT', 'PL'))
    ops = leg_head(g, a, X0, 'L' in START)
    if 'L' in START:
        ops.append(('z', F))                          # with the Z(a) folded into the a compute: CZ(g, f)
    tog_a = [i for i, ev in enumerate(seq) if ev[0] == 'tog' and ev[1] == a]
    assert tog_a and not any(ev[0] == 'cx' and ev[1] == a for ev in seq[:tog_a[0]] + seq[tog_a[-1]:])
    ev = seq[tog_a[0]]
    assert not ev[3]
    ops += rccx_pair(g, 1, ev[2], ev[4], ev[5], F, a)   # a: c1 -> 0 (controls f, ~g) fused with a: 0 -> w23
    ops.append(('h', F))
    for i, ev in enumerate(seq):
        if ev[0] == 'rz':
            ops.append(('rz', terms[ev[1]], F))
        elif ev[0] == 'cx':
            ops.append(('cx', ev[1], F))
        elif i not in (tog_a[0], tog_a[-1]):
            # toggle of a control wire inside the window: the once-used-control Z residual is dropped after the
            # in-toggle and before the out-toggle (adjacent through control-only uses: they cancel)
            ops += rccx(ev[2], ev[3], ev[4], ev[5], ev[1], z='droppost' if ev[6] else None)
    ops.append(('h', F))
    ev = seq[tog_a[-1]]
    ops += inverse(rccx_pair(g, 1, ev[2], ev[4], ev[5], F, a))
    if 'L' in end:
        ops.append(('z', F))
    ops += inverse(leg_head(g, a, X1, 'L' in end))
    return ops


DIAG = {'t': 1, 'tdg': 7, 's': 2, 'sdg': 6, 'z': 4}
PH = {0: [], 1: ['t'], 2: ['s'], 3: ['s', 't'], 4: ['z'], 5: ['z', 't'], 6: ['sdg'], 7: ['tdg']}


def peephole(ops, n):
    """merge diagonal Clifford+T phases per wire (they commute through CX controls); exact, no CX/T change here."""
    acc = [0] * n
    out = []

    def flush(q):
        for gname in PH[acc[q] % 8]:
            out.append((gname, q))
        acc[q] = 0

    for o in ops:
        if o[0] in DIAG:
            acc[o[1]] += DIAG[o[0]]
            continue
        if o[0] == 'cx':
            flush(o[2])
        else:
            flush(o[2] if o[0] == 'rz' else o[1])
        out.append(o)
    for q in range(n):
        flush(q)
    return out


def build(spec):
    b = Builder(spec)
    a, g = b.alloc(2, "ag")
    ops = peephole(circuit_ops(spec.beta, a, g), max(a, g) + 1)
    for o in ops:
        if o[0] == 'rz':
            b.rz(o[1], o[2])
        else:
            getattr(b, o[0])(*o[1:])
    b.free([a, g])
    return b
