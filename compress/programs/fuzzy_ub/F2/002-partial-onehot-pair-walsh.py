"""SUMMARY: F1 datapath (parity frame, 8 Fredkin q2-permutation frames, Bell decode) with a partial sector one-hot: (t,l) lines of the same-frame sector pairs {2,3},{6,7} are not split by p_r; each pair is one Walsh-Gray R_x over (line&w23 or line, p_r, w01) with shared Bell-pair ANDs; beta-free segments re-synthesised (7-CX Fredkins).
DISCOVERY: sectors {2,3} and {6,7} differ only in p_r and share the frame rho=(3,0,1,2) with decoded pairs (0,1),(2,3); leaving their (t,l) one-hot lines unsplit by p_r (-16 CX) and doing one Walsh-Gray R_x per pair over (line&w23 | line, p_r, w01) costs 16 CX rotations + 18 CX ANDs for all four sectors.
DISCOVERY: exhaustive DP over sector order and relative f-controlled q2 permutations (2 valid rho per sector, 8 for p3, 1 for p6) shows 8 Fredkins is minimal, also with the {2,3,6,7} block forced; no rho is shared by sectors 0&1 or 4&5.
DISCOVERY: level-3 resynthesis of the beta-free segments saves 1 CX per Fredkin (8->7); 4-CX relative-phase Toffolis in paired same-wire Fredkins do not cancel (error ~1).
"""
FAMILY = "F2"
PARENT = "r01-F1-001"
import numpy as np
from qiskit import QuantumCircuit, transpile
from su2plaq.compress.builder import Builder


class Rec:
    """records ops; rotations whose angle depends on beta are marked as segment barriers."""
    def __init__(self, n, anc):
        self.ops = []
        self.free_anc = list(anc)

    def alloc(self, k=1, name=None):
        out = self.free_anc[:k]; self.free_anc = self.free_anc[k:]; return out

    def free(self, qs):
        self.free_anc = list(qs) + self.free_anc

    def __getattr__(self, name):
        def f(*args):
            self.ops.append((name, args))
        return f


BASIS = ['cx', 'h', 'rz', 'x', 's', 'sdg', 't', 'tdg', 'z']


def _emit_seg(b, seg, nq):
    if not seg:
        return
    qc = QuantumCircuit(nq)
    for name, args in seg:
        getattr(qc, name)(*args)
    best = None
    for seed in range(4):
        t = transpile(qc, basis_gates=BASIS, optimization_level=3, seed_transpiler=seed)
        key = (t.count_ops().get('cx', 0), len(t.data))
        if best is None or key < best[0]:
            best = (key, t)
    t = best[1]
    for ins in t.data:
        nm = ins.operation.name
        qs = [t.find_bit(q).index for q in ins.qubits]
        if nm == 'rz':
            th = float(ins.operation.params[0])
            k = th / (np.pi / 4)
            if abs(k - round(k)) < 1e-9:
                k = int(round(k)) % 8
                for g in {0: [], 1: ['t'], 2: ['s'], 3: ['s', 't'], 4: ['z'], 5: ['z', 't'], 6: ['sdg'], 7: ['tdg']}[k]:
                    getattr(b, g)(qs[0])
            else:
                b.rz(th, qs[0])
        else:
            getattr(b, nm)(*qs)

F = 1
PR, PT, PL = 3, 5, 7

PLAN = [('m', [(2, 3), (0, 1)]), (0, [(1, 2)], 1), ('m', [(0, 2)]), (1, [(0, 1)], -1), ('m', [(1, 3)]),
        (5, [(0, 1)], 1), ('m', [(0, 2)]), ('J',), (4, [(1, 2)], -1), ('m', [(0, 3), (1, 3), (2, 3)])]


def q2(i):
    return 2 * i


def cswap(b, i, j):
    a, d = q2(i), q2(j)
    b.cx(d, a); b.ccx(F, a, d); b.cx(d, a)


def mc_rx_pp(b, theta, cs, t):
    """C^n R_x(theta) on t, controls cs (all on |1>), as a Gray-code phase polynomial (2^n CX)."""
    n = len(cs)
    b.h(t)
    g = [k ^ (k >> 1) for k in range(2 ** n)]
    for idx, s in enumerate(g):
        b.rz(theta * (-1) ** bin(s).count('1') / 2 ** n, t)
        nxt = g[(idx + 1) % len(g)]
        bit = (s ^ nxt).bit_length() - 1
        b.cx(cs[bit], t)
    b.h(t)


def mc_rx_fn(b, fn, cs, t):
    """R_x(fn(x)) on t for every basis value x of the controls cs: Walsh-Gray phase polynomial (2^n CX)."""
    n = len(cs)
    vals = np.array([fn([(x >> k) & 1 for k in range(n)]) for x in range(2 ** n)], dtype=float)
    b.h(t)
    g = [k ^ (k >> 1) for k in range(2 ** n)]
    for idx, s in enumerate(g):
        a = sum(vals[x] * (-1) ** bin(s & x).count('1') for x in range(2 ** n)) / 2 ** n
        if abs(a) > 1e-12:
            b.rz(a, t)
        nxt = g[(idx + 1) % len(g)]
        bit = (s ^ nxt).bit_length() - 1
        b.cx(cs[bit], t)
    b.h(t)


def onehot(b, anc, inverse=False):
    """Sector one-hot b_p = [p_r p_t p_l == p] in clean ancillas, partly in place on the p_t/p_l wires.
    Returns map p -> qubit."""
    a11, a00 = anc[0], anc[1]
    ops = [('rccx', PT, PL, a11), ('cx', a11, PT), ('cx', a11, PL),          # PT <- t&~l, PL <- l&~t
           ('cx', PT, a00), ('cx', PL, a00), ('cx', a11, a00), ('x', a00)]   # a00 <- ~t&~l
    where = {}
    where[6] = where[7] = a11                                                # (t,l)=(1,1): not split by p_r
    where[2] = where[3] = PT                                                 # (t,l)=(1,0): not split by p_r
    for k, (q, tl) in enumerate([(PL, 4), (a00, 0)]):
        b1 = anc[2 + k]
        ops += [('rccx', q, PR, b1), ('cx', b1, q)]                            # b1 <- q&r, q <- q&~r
        where[tl + 1], where[tl] = b1, q
    if inverse:
        ops = ops[::-1]
    for o in ops:
        getattr(b, o[0])(*o[1:])
    return where


def build(spec):
    B = Builder(spec)
    beta = spec.beta
    anc_all = B.alloc(7, "anc")
    nq = 8 + 7
    b = Rec(nq, anc_all)
    for k in (PR, PT, PL): b.cx(F, k)
    anc = b.alloc(4, "onehot")
    hot = onehot(b, anc)
    dec = []
    ands = {}

    def drop_and(pr):
        w = ands.pop(pr)
        i, j = pr
        b.rccx(q2(i), q2(j), w)
        b.free([w])

    def undo(pr):
        if pr in ands: drop_and(pr)
        i, j = pr
        b.h(q2(i)); b.cx(q2(i), q2(j)); dec.remove(pr)

    for step in PLAN:
        if step[0] == 'm':
            for pr in list(dec): undo(pr)
            for i, j in step[1]: cswap(b, i, j)
            continue
        if step[0] == 'J':
            # sectors 2,3 (line PT) and 6,7 (line a11) share frame and decoded pairs (0,1),(2,3)
            for pr in [(2, 3), (0, 1)]:
                if pr not in dec:
                    i, j = pr; b.cx(q2(i), q2(j)); b.h(q2(i)); dec.append(pr)
            w23, w01, u = b.alloc(3)
            t2, t3, t6, t7 = 8 * beta, -16 * beta, -4 * beta, 8 * beta
            b.rccx(q2(0), q2(1), w01)
            mc_rx_fn(b, lambda x: x[0] * (t6 * (1 - x[1]) + t7 * x[1] * x[2]), [hot[6], PR, w01], F)
            b.rccx(q2(2), q2(3), w23); b.rccx(hot[2], w23, u)
            mc_rx_fn(b, lambda x: x[0] * (t2 * (1 - x[1]) + t3 * x[1] * x[2]), [u, PR, w01], F)
            b.rccx(hot[2], w23, u); b.rccx(q2(2), q2(3), w23)
            b.rccx(q2(0), q2(1), w01)
            b.free([w23, w01, u])
            continue
        p, pairs, s = step[:3]
        use_and = step[3] if len(step) > 3 else []
        for pr in list(ands):
            if pr not in use_and: drop_and(pr)
        need = set(x for pr in pairs for x in pr)
        for pr in list(dec):
            if pr not in pairs and (pr[0] in need or pr[1] in need): undo(pr)
        for pr in pairs:
            if pr not in dec:
                i, j = pr; b.cx(q2(i), q2(j)); b.h(q2(i)); dec.append(pr)
        for pr in use_and:
            if pr not in ands:
                w = b.alloc(1)[0]
                b.rccx(q2(pr[0]), q2(pr[1]), w)
                ands[pr] = w
        theta = -4.0 * beta * s * 2 ** len(pairs)
        ctr = [hot[p]]
        for pr in pairs:
            if pr in ands: ctr.append(ands[pr])
            else: ctr += [q2(pr[0]), q2(pr[1])]
        if len(ctr) == 1:
            b.crx(theta, ctr[0], F)
        else:
            mc_rx_pp(b, theta, ctr, F)
    for pr in list(ands): drop_and(pr)
    for pr in list(dec): undo(pr)
    onehot(b, anc, inverse=True)
    b.free(anc)
    for k in (PR, PT, PL): b.cx(F, k)
    seg = []
    for name, args in b.ops:
        if name in ('rz', 'crx'):
            _emit_seg(B, seg, nq); seg = []
            getattr(B, name)(*args)
        else:
            seg.append((name, args))
    _emit_seg(B, seg, nq)
    B.free(anc_all)
    return B
