"""SUMMARY: frame D (link prep, corner CX/CCX/C2H, GHZ fold of the Q flags; U_E = 4 phases on the flags) sends 80 bright pairs to basis pairs; per r-class (7) merged Toffolis make partners differ only in F=q1, a 4-7 literal rccx AND (shared invariant prefixes) flags the class and one crx(-2 kappa s beta) rotates it; closed pair by an unconditional CX.CH.H basis change and one crx; then D^dagger.
DISCOVERY: in the frame, within each kappa=2 class r the partner flip on the equal-corner e1 bits is tau_c = a_c xor e1_d (d a fixed different corner), so Toffolis CCX(e1_d, F -> e1_c) make every pair of the class differ only in F; the post-Toffoli bright set of each class is isolated from all 1296 valid images by a cube of 4-7 literals (single bits / 2-3 bit parities).
DISCOVERY: the frame coupling sign of a kappa=2 class is (-1)^{r_l} (r_l = g_b xor g_l); after CX(e1c0, F -> e1c1, e1c2, e1c3) the closed pair is u = (|a>+|b>)/sqrt2, v = -|c> with a, b, c (and one dark label d) differing only in (F, e1c0).
DISCOVERY: the closed pair needs no controlled H: the unconditional V = CX(F,q0) CH(F,q0) H(q0) maps u -> |00>, v -> -|10> and both dark states of the 4-label block to q0 = 1, so one crx controlled by (flag and not q0) on F does the 3x3 block.
"""
FAMILY = "F5"
PARENT = None

import math

import numpy as np

from su2plaq.compress.builder import Builder
from su2plaq.compress.spec import get_encoding

F = 1                                   # flip qubit (= g_b after the GHZ fold)
E1 = (0, 2, 6, 8)                       # corner e1 bits c0..c3
R = (5, 9, 13)                          # r = (g_r^g_b, g_t^g_b, g_l^g_b)
CORN = [(0, 12, 1, 13), (2, 4, 1, 5), (6, 10, 5, 9), (8, 14, 9, 13)]   # (e1, e2, g_X, g_Y)

# per class r = (q5, q9, q13): Toffoli rule [(e1_c qubit, a, b)] with tau_c = a ^ b*e1_d, d qubit, and the class cube
# (literals (qubits, parity value)) on the post-Toffoli labels (found in scratch/proposer/f5_class.py, milp set cover).
CLASSES = {
    (0, 0, 1): (0, [(2, 0, 1), (6, 0, 1)], [((13,), 1), ((9,), 0), ((4,), 1), ((10,), 1), ((2, 6), 0), ((6, 8), 0)]),
    (0, 1, 0): (6, [(0, 0, 1), (2, 1, 1)], [((13,), 0), ((5,), 0), ((9,), 1), ((4,), 1), ((12,), 1), ((0, 8), 0), ((2, 8), 1)]),
    (0, 1, 1): (0, [(2, 0, 1), (8, 1, 1)], [((13,), 1), ((5,), 0), ((9,), 1), ((4,), 1), ((8,), 1), ((2, 6, 14), 1)]),
    (1, 0, 0): (2, [(0, 0, 1), (8, 1, 1)], [((5,), 1), ((9,), 0), ((12,), 1), ((14,), 1), ((0, 8), 1), ((0, 2, 13), 1)]),
    (1, 0, 1): (None, [], [((5,), 1), ((9,), 0), ((13,), 1), ((2, 8), 0)]),
    (1, 1, 0): (2, [(0, 0, 1), (6, 0, 1)], [((5,), 1), ((9,), 1), ((13,), 0), ((10,), 1), ((12,), 1), ((0, 2, 6), 0)]),
    (1, 1, 1): (0, [(6, 1, 1), (8, 1, 1)], [((5,), 1), ((13,), 1), ((6,), 1), ((8,), 1), ((10,), 1), ((14,), 1)]),
}
# closed pair: after CX(q0 -> q2,q6,q8), CX(q1 -> q2,q6,q8) the labels a, b, c share every bit except (q1, q0)
CLOSED_CUBE = [((4,), 1), ((6,), 1), ((8,), 1), ((10,), 1), ((12,), 1), ((2, 13), 1), ((9, 12, 14), 0)]
CLOSED_MOVES = [(0, 2), (0, 6), (0, 8), (1, 2), (1, 6), (1, 8)]


def _c2h(ops, c1, c2, t):
    """doubly controlled H = Ry(pi/4) CCZ Ry(-pi/4) on t, Ry(+-pi/4) = S H T^(+-1) H Sdg (phases cancel)."""
    ops += [("sdg", (t,)), ("h", (t,)), ("tdg", (t,)), ("h", (t,)), ("s", (t,)), ("ccz", (c1, c2, t)),
            ("sdg", (t,)), ("h", (t,)), ("t", (t,)), ("h", (t,)), ("s", (t,))]


def _frame():
    """(link prep ops, rest of the frame ops) as (name, qubits)."""
    prep = []
    for l in range(4):
        L1, L2, R1, R2 = 4 * l, 4 * l + 1, 4 * l + 2, 4 * l + 3
        prep += [("cx", (L1, L2)), ("cx", (R1, R2)), ("cx", (L2, R2))]   # L2 := g_l (1 iff Q), R2 := 0 (valid codes)
    rest = []
    for e1, e2, gX, gY in CORN:
        rest += [("cx", (e1, e2)), ("ccx", (gX, e2, e1))]
    for e1, e2, gX, gY in CORN:
        _c2h(rest, gX, gY, e1)
    for q in R:
        rest.append(("cx", (F, q)))
    return prep, rest


_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}


def _inverse(ops):
    return [(_INV.get(n, n), q) for n, q in reversed(ops)]


# ---------------------------------------------------------------- emission-time classical check of the frame (numpy)
_H = np.array([[1, 1], [1, -1]]) / math.sqrt(2)
_PH = {"s": 1j, "sdg": -1j, "t": np.exp(1j * math.pi / 4), "tdg": np.exp(-1j * math.pi / 4)}


def _sim(ops, st):
    for n, qs in ops:
        out = {}
        for x, a in st.items():
            if n == "cx":
                y = x ^ (((x >> qs[0]) & 1) << qs[1]); out[y] = out.get(y, 0) + a
            elif n == "ccx":
                y = x ^ ((((x >> qs[0]) & (x >> qs[1])) & 1) << qs[2]); out[y] = out.get(y, 0) + a
            elif n == "ccz":
                s = -1 if ((x >> qs[0]) & (x >> qs[1]) & (x >> qs[2]) & 1) else 1; out[x] = out.get(x, 0) + s * a
            elif n in _PH:
                out[x] = out.get(x, 0) + (_PH[n] if (x >> qs[0]) & 1 else 1) * a
            elif n == "h":
                q = qs[0]; b = (x >> q) & 1; x0 = x & ~(1 << q)
                out[x0] = out.get(x0, 0) + _H[0, b] * a
                out[x0 | (1 << q)] = out.get(x0 | (1 << q), 0) + _H[1, b] * a
            else:
                raise ValueError(n)
        st = {x: a for x, a in out.items() if abs(a) > 1e-12}
    return st


def _snap_kappa(k):
    for val in (1.0, 2.0, 4.0 * math.sqrt(2.0)):
        if abs(k - val) < 1e-9:
            return val
    raise ValueError(f"unexpected kappa {k}")


def _class_angles():
    """kappa * sign per class r (and for the closed pair), read from the oracle's bright pairs through the frame."""
    enc = get_encoding("rishon")
    codes = [int(c) for c in enc.inner_codes()]
    prep, rest = _frame()
    ops = prep + rest
    ks = {}
    closed = None
    for u, v, k in enc.bright_pairs():
        k = _snap_kappa(k)
        iu = _sim(ops, {codes[i]: u[i] for i in np.flatnonzero(np.abs(u) > 1e-12)})
        iv = _sim(ops, {codes[i]: v[i] for i in np.flatnonzero(np.abs(v) > 1e-12)})
        if len(iu) == 2 and len(iv) == 1:              # the closed pair
            closed = (k, iu, iv)
            continue
        if len(iu) != 1 or len(iv) != 1:
            raise ValueError("frame does not send the pair to basis states")
        (xu, au), = iu.items()
        (xv, av), = iv.items()
        x0, x1 = (xu, xv) if not (xu >> F) & 1 else (xv, xu)
        r = tuple((x0 >> q) & 1 for q in R)
        qd, rule, _ = CLASSES[r]

        def tx(x):
            if (x >> F) & 1:
                ed = (x >> qd) & 1 if qd is not None else 0
                for qc, a, b in rule:
                    if a ^ (b & ed):
                        x ^= 1 << qc
            return x

        if tx(x0) ^ tx(x1) != 1 << F:
            raise ValueError(f"class {r}: Toffoli rule does not reduce the partner map to X_F")
        ks.setdefault(r, set()).add(round(k * float(np.sign(np.real(au * av))), 9))
    out = {}
    for r, s in ks.items():
        if len(s) != 1:
            raise ValueError(f"class {r}: several couplings {s}")
        out[r] = s.pop()
    k, iu, iv = closed
    (xc, ac), = iv.items()
    amps = list(iu.values())
    out["closed"] = k * float(np.sign(np.real(amps[0] * ac)))
    return out


# ---------------------------------------------------------------- circuit pieces
ORDER = [(0, 0, 1), (1, 1, 1), (0, 1, 1), (0, 1, 0), (1, 0, 1), (1, 0, 0), (1, 1, 0)]   # minimises CX (Toffoli transitions + shared prefixes)


def _emit(b, ops):
    for n, qs in ops:
        getattr(b, n)(*qs)


INV = (4, 5, 9, 10, 12, 13, 14)          # r and e2 qubits: never changed by the rotation stage
# invariant-literal order per class (shared prefixes between consecutive flags stay computed; scratch/proposer/f5_prefix.py)
PREFIX = {
    (0, 0, 1): [(13, 1), (10, 1), (9, 0), (4, 1)],
    (1, 1, 1): [(13, 1), (10, 1), (5, 1), (14, 1)],
    (0, 1, 1): [(5, 0), (9, 1), (4, 1), (13, 1)],
    (0, 1, 0): [(5, 0), (9, 1), (4, 1), (13, 0), (12, 1)],
    (1, 0, 1): [(5, 1), (9, 0), (13, 1)],
    (1, 0, 0): [(5, 1), (9, 0), (12, 1), (14, 1)],
    (1, 1, 0): [(10, 1), (12, 1), (5, 1), (9, 1), (13, 0)],
    "closed": [(10, 1), (12, 1), (4, 1)],
}


class _AndStack:
    """Stack of literals; entry i holds (qubit, value, t_i) with t_i = AND of literals 0..i (t_0 = the literal qubit).
    AND targets are rccx'd into the zeroed R2 qubits first, then into clean ancillas; every push is mirrored by a pop."""

    def __init__(self, b):
        self.b = b
        self.st = []
        self.pool = [3, 7, 11, 15]

    def push(self, q, val):
        b = self.b
        if val == 0:
            b.x(q)
        if not self.st:
            self.st.append((q, val, q, None))
            return
        if self.pool:
            t, kind = self.pool.pop(0), "free"
        else:
            t, kind = b.alloc(1, "and")[0], "anc"
        b.rccx(self.st[-1][2], q, t)
        self.st.append((q, val, t, kind))

    def pop(self):
        b = self.b
        q, val, t, kind = self.st.pop()
        if kind is not None:
            b.rccx(self.st[-1][2], q, t)
            if kind == "free":
                self.pool.insert(0, t)
            else:
                b.free([t])
        if val == 0:
            b.x(q)

    def top(self):
        return self.st[-1][2]

    def qubits(self):
        return {e[0] for e in self.st}

    def set_prefix(self, lits):
        n = 0
        while n < len(self.st) and n < len(lits) and self.st[n][:2] == tuple(lits[n]):
            n += 1
        while len(self.st) > n:
            self.pop()
        for q, val in lits[n:]:
            self.push(q, val)


def _flag_on(stk, key, cube):
    """Bring the stack to PREFIX[key] + the cube's other literals (parities folded in place); returns finish()."""
    b = stk.b
    pre = PREFIX[key]
    stk.set_prefix(pre)
    rest = [(qs, v) for qs, v in cube if not (len(qs) == 1 and (qs[0], v) in pre)]
    assert len(rest) + len(pre) == len(cube), key
    used = [q for qs, _ in rest for q in qs]
    undo = []
    extra = []
    lits = []
    for qs, val in rest:
        if len(qs) == 1:
            lits.append((qs[0], val))
            continue
        cand = [t for t in qs if used.count(t) == 1 and t not in INV] + \
               [t for t in qs if used.count(t) == 1 and t not in stk.qubits()]
        if cand:
            tgt = cand[0]
            srcs = [q for q in qs if q != tgt]
        else:
            tgt = b.alloc(1, "parity")[0]
            extra.append(tgt)
            srcs = list(qs)
        for q in srcs:
            b.cx(q, tgt)
            undo.append((q, tgt))
        lits.append((tgt, val))
    n0 = len(stk.st)
    for q, val in lits:
        stk.push(q, val)

    def finish():
        while len(stk.st) > n0:
            stk.pop()
        for q, t in reversed(undo):
            b.cx(q, t)
        if extra:
            b.free(extra)

    return finish


def _gates(qd, rule):
    """Toffoli rule as a set of commuting gates ('T', d, c) = CCX(d, F, c) and ('C', c) = CX(F, c)."""
    g = set()
    for qc, a, bb in rule:
        if bb:
            g.add(("T", qd, qc))
        if a:
            g ^= {("C", qc)}
    return g


def _emit_set(b, gs):
    ts = sorted(g for g in gs if g[0] == "T")
    for d in sorted({t[1] for t in ts}):
        cs = [t[2] for t in ts if t[1] == d]
        for c in cs[1:]:
            b.cx(cs[0], c)
        b.ccx(d, F, cs[0])
        for c in cs[1:]:
            b.cx(cs[0], c)
    for g in sorted(g for g in gs if g[0] == "C"):
        b.cx(F, g[1])


def _transition(b, cur, nxt):
    """Emit cur^-1 . nxt (all gates of one set commute; sets with the same control d also commute with each other)."""
    ds = {g[1] for g in cur | nxt if g[0] == "T"}
    if len(ds) <= 1:
        _emit_set(b, cur ^ nxt)
    else:
        _emit_set(b, cur)
        _emit_set(b, nxt)


def build(spec):
    b = Builder(spec)
    beta = spec.beta
    ks = _class_angles()
    prep, rest = _frame()
    # frame D = rest . prep, with U_E (phase -3/4 alpha on each Q flag L2) after link prep
    _emit(b, prep)
    for l in range(4):
        b.p(-0.75 * spec.alpha, 4 * l + 1)
    _emit(b, rest)
    # per-class rotations: exp(i beta kappa s X_F) = Rx(-2 kappa s beta) on the class's post-Toffoli labels
    cur = set()
    stk = _AndStack(b)
    for r in ORDER:
        qd, rule, cube = CLASSES[r]
        nxt = _gates(qd, rule)
        _transition(b, cur, nxt)
        cur = nxt
        finish = _flag_on(stk, r, cube)
        b.crx(-2.0 * ks[r] * beta, stk.top(), F)
        finish()
    _transition(b, cur, set())
    # closed pair: moves, flag (cube on the moved labels, no F / q0 literal), basis change V, crx on F if flag and not q0, undo
    for c, t in CLOSED_MOVES:
        b.cx(c, t)
    finish = _flag_on(stk, "closed", CLOSED_CUBE)
    flag = stk.top()
    # V = CX(F, q0) CH(F, q0) H(q0) (unconditional, undone below): u -> |F=0, q0=0>, v -> -|F=1, q0=0>, w and the 4th label -> q0=1
    b.h(0)
    b.ch(F, 0)
    b.cx(F, 0)
    b.x(0)
    a2 = b.alloc(1, "closed")[0]
    b.rccx(flag, 0, a2)
    b.crx(-2.0 * ks["closed"] * beta, a2, F)
    b.rccx(flag, 0, a2)
    b.free([a2])
    b.x(0)
    b.cx(F, 0)
    b.ch(F, 0)
    b.h(0)
    finish()
    stk.set_prefix([])
    for c, t in reversed(CLOSED_MOVES):
        b.cx(c, t)
    # D^dagger
    _emit(b, _inverse(rest))
    _emit(b, _inverse(prep))
    return b
