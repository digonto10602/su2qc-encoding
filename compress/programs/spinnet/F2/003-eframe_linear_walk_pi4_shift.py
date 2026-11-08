"""SUMMARY: dimer frame (pivot b; q1 = E = b^r and q2 = U = b^t both fused into 2-CX Bravyi-Maslov end blocks, flags computed after the frame H) with one clean flag N=[c1=c3=0] and A=[U=V=0] XORed in place into corner c1; all-linear 13-toggle walk E -> 0 over (E, N, c1^A, c0, c2) (the mirror of the F1 walk) with the minimum-T coefficient choice; every rotation picks its X-flip sign and a pi/4 shift rz(th) = rz(th +- pi/4) tdg/t when the shifted Clifford+T word is cheaper, and U_E is p(-3alpha/4 + pi/4) tdg (58 + 1 T instead of 64); 31 CX, 13 + 4 rotations, 17 qubits
DISCOVERY: pygridsynth's T-count at eps = 1e-6 depends on the angle modulo pi/4: p(-3alpha/4) costs 64 T but p(-3alpha/4 + pi/4) costs 58 (+1 explicit tdg), and rz(+-beta/2) 66 vs 64 (+1); shifting the four U_E phases alone saves 20 T at equal CX on any spinnet circuit (the F1-type walk goes 1086 -> 1062 T with the walk shifts).
DISCOVERY: flags may be computed after the frame H, so both pivot ladder CX (E and U) fuse with the walk ends (each 3-qubit end block is a 2-CX Clifford) and the walk may start/end anywhere in span(E, U); still, exhaustive DFS finds no 30-CX all-linear 12-toggle walk for flag N13 with A in c1 or c3 (atoms E, U, N, c^A, raw corners), none for N02 with ends {0, E}, and among the N13 and N02 configurations the only 13-toggle walks are the 12 F1-type ones (N13, A in c1); minimum (12-term) supports need 18-23 toggles.
DISCOVERY: 3-unit family (NOR flag pair, A in place in a flag corner, direct 3-AND through a third corner with all literal/order variants, free ends span(E, U), and the control-order swap of the in-place A pair, phase (U^V) c_host, as a free fix): no 31-CX walk in all 24 configurations with <= 1 extra atom (DFS), so 32 CX stays that family's floor.
"""
import numpy as np

from su2plaq.compress.builder import Builder

FAMILY = 'F2'
PARENT = 'r02-F2-002'

FLAG = ((1, 0), (3, 0))
ALIT = (0, 0)
HOST = 1
START = 'E'
WALK = ['c1', 'E', 'N', 'c1', 'c0', 'N', 'c2', 'c1', 'N', 'c1', 'c0', 'N', 'c2']
ROT = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
FLIP = {0: 0, 1: 0, 3: 0, 4: 1, 5: 1, 6: 0, 7: 0, 8: 0, 9: 0, 10: 1, 11: 1, 12: 0, 13: 0}
SHIFT = {0: 0, 1: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 0, 8: 0, 9: 0, 10: 0, 11: 1, 12: 1, 13: 0}
CZS = []
ZS = []
# optimal Clifford blocks (Bravyi-Maslov) of the fused ladder ends, 2 CX each
START_OPS = [('z', (0,)), ('h', (1,)), ('s', (1,)), ('cx', (0, 2)), ('cx', (0, 1)), ('sdg', (1,)), ('h', (1,)), ('sdg', (0,)), ('h', (0,))]
END_OPS = {(0, 0): [('h', (0,)), ('cx', (0, 2)), ('cx', (0, 1))], (0, 1): [('x', (0,)), ('h', (0,)), ('s', (0,)), ('h', (2,)), ('s', (2,)), ('cx', (0, 2)), ('sdg', (2,)), ('h', (2,)), ('cx', (0, 1))], (1, 0): [('x', (0,)), ('h', (0,)), ('s', (0,)), ('h', (1,)), ('s', (1,)), ('cx', (0, 2)), ('cx', (0, 1)), ('sdg', (1,)), ('h', (1,))], (1, 1): [('x', (0,)), ('h', (0,)), ('h', (1,)), ('s', (1,)), ('h', (2,)), ('s', (2,)), ('cx', (0, 2)), ('sdg', (2,)), ('h', (2,)), ('cx', (0, 1)), ('sdg', (1,)), ('h', (1,))]}


CORNER_LINKS = {0: (0, 3), 1: (0, 1), 2: (1, 2), 3: (2, 3)}   # corner c_k touches links (b r t l = 0 1 2 3)


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


def _qubit_values(y, c):
    """Walk-time contents of the control qubits (dimer frame, flags in place)."""
    b = [(y >> i) & 1 for i in range(4)]
    cc = [(c >> k) & 1 for k in range(4)]
    E, U, V = b[0] ^ b[1], b[0] ^ b[2], b[1] ^ b[3]
    A = int(U == ALIT[0] and V == ALIT[1])
    (i, li), (j, lj) = FLAG
    d = {"E": E, "U": U, "V": V, "N": int(cc[i] == li and cc[j] == lj)}
    for k in range(4):
        d["c%d" % k] = cc[k] ^ (A if k == HOST else 0)
    return d


def _atom(name, d):
    if name.startswith("["):
        x, y = name[1:-1].split("&")
        return (1 - d[x[1:]] if x[0] == "~" else d[x]) & (1 - d[y[1:]] if y[0] == "~" else d[y])
    v = 0
    for t in name.split("^"):
        v ^= d[t] if t != "0" else 0
    return v


def _walk():
    """Pivot parity masks (over the 47 codes) of every walk state, the target f (K on bright codes, 0 on dark)."""
    rows = _rows()
    D = [_qubit_values(y, c) for (y, c) in rows]
    f = np.array([_kappa(y) if c == 0 else 0.0 for (y, c) in rows])
    m = np.array([_atom(START, d) for d in D])
    out = [m.copy()]
    for g in WALK:
        m = m ^ np.array([_atom(g, d) for d in D])
        out.append(m.copy())
    return D, f, out


def _coeffs():
    """Rotation coefficients a_k (pivot polynomial f = sum_k a_k Z_k over the states ROT of the walk), exact multiples of 1/8."""
    D, f, st = _walk()
    W = np.array([1 - 2 * st[k] for k in ROT], float).T
    a, *_ = np.linalg.lstsq(W, f, rcond=None)
    assert np.abs(W @ a - f).max() < 1e-12
    k8 = np.round(a * 8)
    assert np.abs(a * 8 - k8).max() < 1e-9
    return D, st, dict(zip(ROT, k8 / 8))


def _block(b, ops):
    for name, qs in ops:
        getattr(b, name)(*qs)


def build(spec):
    D, st, co = _coeffs()
    b = Builder(spec)
    (anc,) = b.alloc(1, "N")
    Q = {"E": 1, "U": 2, "V": 3, "N": anc, "c0": 4, "c1": 5, "c2": 6, "c3": 7}
    for q in range(4):                      # U_E: p(-3/4 alpha) per j=1/2 inner link, as p(-3/4 alpha + pi/4) tdg
        b.p(-0.75 * spec.alpha + np.pi / 4, q)  # (the pi/4-shifted angle has a shorter Clifford+T word: 58 + 1 T vs 64)
        b.tdg(q)
    (i, li), (j, lj) = FLAG
    fx = [4 + k for k, l in ((i, li), (j, lj)) if l == 0]
    ax = [q for q, l in ((2, ALIT[0]), (3, ALIT[1])) if l == 0]

    def flag():
        for q in fx:
            b.x(q)
        b.rccx(4 + i, 4 + j, anc)           # N = [c_i = li][c_j = lj]
        for q in fx:
            b.x(q)

    def host():
        for q in ax:
            b.x(q)
        b.rccx(2, 3, 4 + HOST)              # c_host ^= A = [U = ALIT0][V = ALIT1] (non-clean target, mirrored pair)
        for q in ax:
            b.x(q)

    flag()
    b.cx(1, 3)                              # V = r^l on q3
    _block(b, START_OPS)                    # = CX(0->1) CX(0->2) H(0) + pivot preload (q1 = E = b^r, q2 = U = b^t), 2 CX
    host()
    flip = [0]

    def rot(k):
        if k in co and co[k] != 0:
            want = FLIP.get(k, 0)
            if want != flip[0]:
                b.x(0); flip[0] = want
            m = SHIFT.get(k, 0)             # rz(th) = rz(th + m pi/4) rz(-m pi/4): shorter Clifford+T word for some m
            b.rz((-1) ** flip[0] * 2.0 * co[k] * spec.beta + m * np.pi / 4, 0)
            {1: b.tdg, -1: b.t, 2: b.sdg, -2: b.s}.get(m, lambda q: None)(0)

    rot(0)
    for k, g in enumerate(WALK):
        if g.startswith("["):
            x_, y_ = g[1:-1].split("&")
            neg = [Q[t[1:]] for t in (x_, y_) if t[0] == "~"]
            for q in neg:
                b.x(q)
            b.rccx(Q[x_.lstrip("~")], Q[y_.lstrip("~")], 0)
            if flip[0]:
                b.z(Q[x_.lstrip("~")])
            for q in neg:
                b.x(q)
        else:
            for t in g.split("^"):
                b.cx(Q[t], 0)
        rot(k + 1)
    for (p, q) in CZS:
        b.cz(Q[p], Q[q])
    for q in ZS:
        b.z(Q[q])
    last = st[-1]
    Ev = np.array([d["E"] for d in D])
    Uv = np.array([d["U"] for d in D])
    post = None
    for cm in (0, 1):
        for pe in (0, 1):
            for pu in (0, 1):
                if post is None and (last == ((pe * Ev) ^ (pu * Uv) ^ cm)).all():
                    post, cmp_ = (pe, pu), cm
    assert post is not None, "walk does not end in span(E, U)"
    if cmp_:
        flip[0] ^= 1
    if flip[0]:
        b.x(0)
    host()
    _block(b, END_OPS[post])               # = unload + H(0) CX(0->1) CX(0->2), 2 CX
    b.cx(1, 3)
    flag()
    b.free([anc])
    return b
