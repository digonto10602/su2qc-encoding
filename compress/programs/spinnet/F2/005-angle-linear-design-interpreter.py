"""SUMMARY: angle-linear rebuild of the F2 31-CX design (dimer frame, pivot b, fused 2-CX start/end blocks, N=[c1=c3=0] in one ancilla, A=[U=V=0] XORed into c1, all-linear 13-toggle walk E -> 0 over (E, N, c1^A, c0, c2)) with every rotation a plain rational multiple of alpha or beta: U_E = 4 x p(-3alpha/4), walk rz(k beta/4), no pi/4-shift t/tdg (which cost +1 T at every angle), generic design interpreter (flags, direct rccx pairs with exact leftover-phase Z fix, fused START/END = inverse pairs); 31 CX, 17 rotations, 17 qubits
DISCOVERY: wide annealing screens (C, f-in-span-of-visited-states, free ends span(E,U), exact direct-pair leftover sign (-1)^(first literal * net pivot change) with Z fixes) find no 30-CX walk for: no flag (L <= 30), A alone hosted anywhere (L <= 21), A plus any 2-literal AND over E,U,V,c0..c3 in any host (2016 designs, 12 toggles), A plus one direct AND pair (840 designs, 12 toggles, host control-swap phase allowed as a fix); time-limited MILP incumbents: raw A and N13 as wires need 15 terms (12 with A hosted in c1), 21 without A*N cross terms, 19-27 for nested direct A/NOR pairs.
DISCOVERY: no 31-CX three-unit walk without a fix gate (corner NOR ancilla + A in any corner/ancilla + any direct AND of two walk-time literals incl. the NOR and the hosted corner, both first controls: 7104 designs, 7 linear toggles, Z fixes only; with 6 toggles + 1 CZ and the control-swap phase, the 3439 designs with NOR N01, N02, N03 also fail), so the direct-AND route stays at 32 CX (CZ) and the 31-CX floor of all-linear two-flag walks keeps 13 walk rotations.
"""
import itertools

import numpy as np

from su2plaq.compress.builder import Builder

FAMILY = 'F2'
PARENT = 'r03-F2-003'

# ---- design (walk-time qubit names: E=q1, U=q2, V=q3, c0..c3 = q4..q7, ancilla flags by name) ----
FLAGS = [("N", "~c1", "~c3", "anc"), ("A", "~U", "~V", "c1")]     # (name, literal1, literal2, host), computed in order
DIRECT = {}                                                       # name -> (literal1 = first control, literal2)
START = "E"                                                       # pivot preload in {0, E, U, EU} (fused start block)
WALK = ['c1', 'E', 'N', 'c1', 'c0', 'N', 'c2', 'c1', 'N', 'c1', 'c0', 'N', 'c2']

BASEQ = {"E": 1, "U": 2, "V": 3, "c0": 4, "c1": 5, "c2": 6, "c3": 7}
CORNER_LINKS = {0: (0, 3), 1: (0, 1), 2: (1, 2), 3: (2, 3)}   # corner c_k touches links (b r t l = 0 1 2 3)
# fused frame blocks on (q0, q1, q2): START[s] = CX(0,2) CX(0,1) H(0) + preload s, END[s] = its inverse (2 CX each, exact)
END_OPS = {(0, 0): [('h', (0,)), ('cx', (0, 2)), ('cx', (0, 1))],
           (0, 1): [('x', (0,)), ('h', (0,)), ('s', (0,)), ('h', (2,)), ('s', (2,)), ('cx', (0, 2)), ('sdg', (2,)), ('h', (2,)), ('cx', (0, 1))],
           (1, 0): [('x', (0,)), ('h', (0,)), ('s', (0,)), ('h', (1,)), ('s', (1,)), ('cx', (0, 2)), ('cx', (0, 1)), ('sdg', (1,)), ('h', (1,))],
           (1, 1): [('x', (0,)), ('h', (0,)), ('h', (1,)), ('s', (1,)), ('h', (2,)), ('s', (2,)), ('cx', (0, 2)), ('sdg', (2,)), ('h', (2,)), ('cx', (0, 1)), ('sdg', (1,)), ('h', (1,))]}
_INV = {'s': 'sdg', 'sdg': 's'}
START_OPS = {k: [(_INV.get(n, n), q) for n, q in reversed(v)] for k, v in END_OPS.items()}
PRELOAD = {"0": (0, 0), "E": (1, 0), "U": (0, 1), "EU": (1, 1)}


def _kappa(y):
    """Bright-pair coupling K(y <-> y^1111) (Lean couplings_2k: 2K = -4, -1, +2)."""
    z = [(y >> i) & 1 for i in range(4)]
    if len(set(z)) == 1:
        return -2.0
    if z[0] == z[2] and z[1] == z[3]:
        return -0.5
    return 1.0


def _rows():
    """The 47 admissible inner codes (y = links, c = corners; corner rule)."""
    out = []
    for c in range(16):
        need = set().union(*[CORNER_LINKS[k] for k in range(4) if c >> k & 1]) if c else set()
        out += [(y, c) for y in range(16) if all(y >> l & 1 for l in need)]
    return out


def _lit(name, d):
    return 1 - d[name[1:]] if name[0] == "~" else d[name]


def _model():
    """Per admissible code: raw frame values and walk-time qubit values (flags applied in order)."""
    raw, walk = [], []
    for (y, c) in _rows():
        b = [(y >> i) & 1 for i in range(4)]
        d = {"E": b[0] ^ b[1], "U": b[0] ^ b[2], "V": b[1] ^ b[3]}
        for k in range(4):
            d["c%d" % k] = (c >> k) & 1
        raw.append(dict(d))
        for (nm, l1, l2, host) in FLAGS:
            v = _lit(l1, d) & _lit(l2, d)
            if host == "anc":
                d[nm] = v
            else:
                d[host] ^= v
        walk.append(d)
    return raw, walk


def _tokval(tok, d):
    if tok in DIRECT:
        l1, l2 = DIRECT[tok]
        return _lit(l1, d) & _lit(l2, d)
    return d[tok]


def _plan():
    rows = _rows()
    raw, wk = _model()
    n = len(rows)
    f = np.array([_kappa(y) if c == 0 else 0.0 for (y, c) in rows])
    pe, pu = PRELOAD[START]
    s = np.array([pe * r["E"] ^ pu * r["U"] for r in raw])
    states = [s.copy()]
    for tok in WALK:
        s = s ^ np.array([_tokval(tok, d) for d in wk])
        states.append(s.copy())
    # distinct states, first occurrence
    first = {}
    for k, st in enumerate(states):
        first.setdefault(st.tobytes(), k)
    idx = sorted(first.values())
    W = np.array([1 - 2 * states[k] for k in idx], float).T
    rank = np.linalg.matrix_rank(W)
    sol = None
    for size in range(1, len(idx) + 1):
        for S in itertools.combinations(range(len(idx)), size):
            a, *_ = np.linalg.lstsq(W[:, S], f, rcond=None)
            if np.abs(W[:, S] @ a - f).max() < 1e-10:
                sol = dict((idx[S[i]], a[i]) for i in range(size))
                break
        if sol is not None or size >= rank:
            break
    assert sol is not None, "f not in the span of the walk states"
    co = {}
    for k, v in sol.items():
        k16 = np.round(v * 16)
        assert abs(v * 16 - k16) < 1e-9
        if k16 != 0:
            co[k] = k16 / 16
    # end of walk must lie in span(E, U) (+ constant -> pivot X flip)
    Ev = np.array([r["E"] for r in raw]); Uv = np.array([r["U"] for r in raw])
    post = None
    for cm in (0, 1):
        for qe in (0, 1):
            for qu in (0, 1):
                if post is None and (states[-1] == ((qe * Ev) ^ (qu * Uv) ^ cm)).all():
                    post = ((qe, qu), cm)
    assert post is not None, "walk does not end in span(E, U)"
    # leftover phase of the direct rccx pairs: (-1)^(first-literal * net pivot change between the pair)
    q = np.zeros(n, int)
    for nm, (l1, l2) in DIRECT.items():
        pos = [i for i, t in enumerate(WALK) if t == nm]
        assert len(pos) == 2
        dS = np.zeros(n, int)
        for t in WALK[pos[0] + 1:pos[1]]:
            dS ^= np.array([_tokval(t, d) for d in wk])
        q ^= np.array([_lit(l1, d) for d in wk]) & dS
    # Z fixes: q = const + sum of walk-time qubit values + raw frame values (GF(2))
    gens = [("w", k) for k in sorted(set(wk[0]))] + [("r", k) for k in sorted(raw[0])]
    G = [np.array([(wk if g == "w" else raw)[i][k] for i in range(n)]) for g, k in gens]
    zfix = None
    for size in range(0, 5):
        for S in itertools.combinations(range(len(G)), size):
            v = np.zeros(n, int)
            for i in S:
                v ^= G[i]
            if ((v ^ q) == 0).all() or ((v ^ q) == 1).all():
                zfix = [gens[i] for i in S]
                break
        if zfix is not None:
            break
    assert zfix is not None, "direct-pair leftover phase is not a product of Z gates"
    return co, post, zfix


def build(spec):
    co, (post, cm), zfix = _plan()
    b = Builder(spec)
    Q = dict(BASEQ)
    for (nm, l1, l2, host) in FLAGS:
        if host == "anc":
            (Q[nm],) = b.alloc(1, nm)
    for q in range(4):                      # U_E: p(-3/4 alpha) on every inner link (j = 1/2 <=> bit 1)
        b.p(-0.75 * spec.alpha, q)

    def lits(l1, l2):
        return [Q[l[1:]] for l in (l1, l2) if l[0] == "~"]

    def flags(order):
        for (nm, l1, l2, host) in order:
            neg = lits(l1, l2)
            for q in neg:
                b.x(q)
            b.rccx(Q[l1.lstrip("~")], Q[l2.lstrip("~")], Q[nm] if host == "anc" else Q[host])
            for q in neg:
                b.x(q)

    b.cx(1, 3)                              # q3 = V = r^l
    for name, qs in START_OPS[PRELOAD[START]]:   # q1 = E = b^r, q2 = U = b^t, H on the pivot b, preload (2 CX)
        getattr(b, name)(*qs)
    flags(FLAGS)

    def rot(k):
        if k in co:
            b.rz(2.0 * co[k] * spec.beta, 0)

    rot(0)
    for k, tok in enumerate(WALK):
        if tok in DIRECT:
            l1, l2 = DIRECT[tok]
            neg = lits(l1, l2)
            for q in neg:
                b.x(q)
            b.rccx(Q[l1.lstrip("~")], Q[l2.lstrip("~")], 0)
            for q in neg:
                b.x(q)
        else:
            b.cx(Q[tok], 0)
        rot(k + 1)
    for g, k in zfix:
        if g == "w":
            b.z(Q[k])
    if cm:
        b.x(0)
    flags(list(reversed(FLAGS)))
    for g, k in zfix:
        if g == "r":
            b.z(BASEQ[k])
    for name, qs in END_OPS[post]:
        getattr(b, name)(*qs)
    b.cx(1, 3)
    b.free([Q[nm] for (nm, l1, l2, host) in FLAGS if host == "anc"])
    return b
