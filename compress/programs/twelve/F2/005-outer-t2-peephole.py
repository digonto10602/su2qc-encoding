"""SUMMARY: Parent datapath (5-CX clean corner frame, in-place flags, in-walk pa, 9-term Walsh walk, CX 111) with t2 read from the corner-2 outer j bits inside the walk (Gauss law t2 = q21 ^ q23), so corner 2's flag sits in place on q8 and the t2 copy ancilla disappears (31 qubits), plus a 1q peephole and corner-2-before-corner-1 scheduling (depth_CT 1663); no CX gain: a numerical corner-gadget search with outer m/j reads found no 7-CX corner.
DISCOVERY: Per-corner gadget search on the exact corner states (writable a, b, t; controls j_A, j_B, outer m and j bits; free U3 layers; flag on a, b or t; partner phases referenced to the parent frame): the parent 5-CX frame followed by any 2 two-qubit gates gives no valid corner (1656 skeletons, residual floor 0.20), and at a NOT corner no one-gate substitution of the 8-gate frame+flag removes the relabel CX (555 skeletons, floor 0.46); outer reads do not shorten the corner below 8 CX in these neighbourhoods.
DISCOVERY: The walk's type bit can be read from the outer register: t2 = q_j(o4) ^ q_j(o5) on every physical state, so each of the two t toggles becomes two CX from the outer bits (+2 CX) while the cx(t2 -> f2) copy (2 CX) and its ancilla vanish (corner 2 flags in place on q8): equal CX/T, one qubit fewer.
DISCOVERY: depth_CT is fixed by one synthesised electric phase word (~167 levels) + ~20 forward levels + the 9-rotation walk on F (~1410 levels) + ~30 backward levels; merging fixed 1q runs (diagonal merge, BFS-shortest Clifford words) and making corner 1's merge the last F-controlled forward gate gain only 3 levels, and moving any electric phase later on its wire makes the depth worse (1833-2010).
"""
FAMILY = "F2"
PARENT = "r04-F2-004"

import itertools

import numpy as np

from su2plaq.compress.builder import Builder

_INV = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
# Walsh support over (pa, pb, z, t2) of the rotation angle, constant term first
SUPP = [(0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0), (0, 1, 0, 1), (0, 1, 1, 1),
        (1, 0, 0, 1), (1, 0, 1, 1), (1, 1, 0, 1), (1, 1, 1, 1)]


def _kappa(pa, pb, z, t):
    """signed coupling of H_B = kappa X_F in this frame (None = never occurs)."""
    if not (pa and pb):
        return None if (z and t) else 0.0          # dark; (g=0, z=1, t2=1) means n1=4, never dark
    if z:
        return 2.0 if t == 0 else -0.5             # n1 = 0 / n1 = 4
    return -(-1.0) ** t                            # n1 = 2: sign (-1)^(t2 + 1)


def _mux_terms():
    """Exact Walsh coefficients on SUPP (free points used)."""
    rows, rhs = [], []
    for x in itertools.product((0, 1), repeat=4):
        k = _kappa(*x)
        if k is None:
            continue
        rows.append([(-1) ** sum(s * xi for s, xi in zip(S, x)) for S in SUPP])
        rhs.append(k)
    A, rhs = np.array(rows, float), np.array(rhs)
    c, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    if np.abs(A @ c - rhs).max() > 1e-12:
        raise RuntimeError("support does not reproduce kappa")
    return dict(zip(SUPP, c))


_M = {"h": np.array([[1, 1], [1, -1]]) / np.sqrt(2), "s": np.diag([1, 1j]), "sdg": np.diag([1, -1j]),
      "t": np.diag([1, np.exp(1j * np.pi / 4)]), "tdg": np.diag([1, np.exp(-1j * np.pi / 4)]),
      "x": np.array([[0, 1], [1, 0]]), "z": np.diag([1, -1])}
_DIAG = {"z": 4, "s": 2, "sdg": 6, "t": 1, "tdg": 7}
_DWORD = {0: [], 1: ["t"], 2: ["s"], 3: ["s", "t"], 4: ["z"], 5: ["z", "t"], 6: ["sdg"], 7: ["tdg"]}


def _mat(word):
    m = np.eye(2, dtype=complex)
    for g in word:
        m = _M[g] @ m
    return m


def _key(m):
    i = np.argmax(np.abs(m.ravel()) > 1e-9)
    m = m / (m.ravel()[i] / abs(m.ravel()[i]))
    return tuple(np.round(m.ravel(), 6))


def _clifford_table():
    """shortest word over {h, s, sdg, x, z} for each single-qubit Clifford (mod phase), BFS"""
    tab = {_key(np.eye(2)): []}
    frontier = [[]]
    while frontier:
        nxt = []
        for w in frontier:
            for g in ("h", "s", "sdg", "x", "z"):
                w2 = w + [g]
                k = _key(_mat(w2))
                if k not in tab:
                    tab[k] = w2
                    nxt.append(w2)
        frontier = nxt
    return tab


def _shorten(run, tab):
    """equivalent (mod phase) word with no more T gates: merge diagonal stretches, re-synthesise Clifford stretches"""
    word = list(run)
    for _ in range(4):
        out, i = [], 0
        while i < len(word):                       # diagonal stretches -> one or two gates
            if word[i] in _DIAG:
                k = 0
                while i < len(word) and word[i] in _DIAG:
                    k += _DIAG[word[i]]; i += 1
                out += _DWORD[k % 8]
            else:
                out.append(word[i]); i += 1
        word, out, seg = out, [], []
        for gname in word + ["|"]:                 # T-free stretches -> shortest Clifford word
            if gname in ("t", "tdg", "|"):
                out += tab[_key(_mat(seg))]; seg = []
                if gname != "|":
                    out.append(gname)
            else:
                seg.append(gname)
        word = out
    if _key(_mat(word)) != _key(_mat(run)) or sum(g in ("t", "tdg") for g in word) > sum(g in ("t", "tdg") for g in run):
        raise RuntimeError("peephole changed the run")
    return word


def _emit(b, ops):
    """emit ops through the Builder with every maximal run of fixed single-qubit gates on a wire shortened"""
    tab = _clifford_table()
    pend = {}

    def flush(q):
        for gname in _shorten(pend.pop(q, []), tab):
            getattr(b, gname)(q)

    for name, params, qs in ops:
        if name in _M:
            pend.setdefault(qs[0], []).append(name)
            continue
        for q in qs:
            flush(q)
        getattr(b, name)(*params, *qs)
    for q in list(pend):
        flush(q)


class _Rec:
    """records gate calls as (name, params, qubits); parametric gates take their angle first"""

    def __init__(self):
        self.ops = []

    def __getattr__(self, name):
        par = name in ("rz", "p")

        def f(*args):
            self.ops.append((name, args[:1] if par else (), args[1:] if par else args))
        return f


def build(spec):
    b = Builder(spec)
    rec = _Rec()
    fwd = []

    def g(name, *qs):
        fwd.append((name, qs))

    # relabel the two NOT corners (c1: leg q0 by j_b, c3: leg q9 by j_l); emitted before the electric phases, which
    # commute with these controls, so the relabel does not wait for the synthesised phase words
    REL = [("cx", 2, 0), ("cx", 11, 9), ("z", 0), ("z", 9)]
    for name, *qs in REL:
        getattr(rec, name)(*qs)
    # electric layer: phase -3/4 alpha per active inner link (diagonal in the q_j bits)
    for q in (2, 5, 8, 11):
        rec.p(-0.75 * spec.alpha, q)

    tau0, z = b.alloc(2, "flags")
    pb, = b.alloc(1, "and")

    def frame(a, bb, j, t):
        """5-CX corner frame on legs (a, bb) with type qubit t and one raw link qubit j of this corner."""
        g("s", a)
        for q in (a, bb):
            g("h", q); g("sdg", q); g("h", q)
        g("cx", a, bb); g("h", a); g("t", a); g("h", a); g("t", bb)
        g("tdg", a); g("cx", t, a); g("t", a)                  # C_t(T X T^dg) inside W
        g("cx", a, bb)
        for q in (a, bb):
            g("h", q); g("s", q); g("h", q)
        g("cx", j, a); g("z", a)                               # C_j(Y_a) (S_a of W cancels against S^dg_a)
        g("ch", t, a); g("sdg", a)                             # C_t(S^dg H S): diff legs end orthogonal to |00>

    def flag(a, bb, target):
        # target holds t: target ^= [legs = 00] gives the bright flag (diff legs never sit on |00>)
        g("x", a); g("x", bb); g("rccx", a, bb, target)

    g("cx", 13, tau0); g("cx", 15, tau0)          # t0 from the outer q_j bits of corner 0
    frame(1, 10, 2, tau0)                         # corner 0: j_b raw on q2
    g("cx", 5, 11)                                # q11 = j_r ^ j_l
    g("cx", 8, 2)                                 # q2 = j_b ^ j_t
    g("x", 2); g("x", 11); g("rccx", 2, 11, z); g("x", 2); g("x", 11)   # z = [t1 = t2 = t3]
    g("cx", tau0, 2)                              # q2 = t3
    frame(7, 9, 8, 2)                             # corner 3: j_t raw on q8
    flag(7, 9, 2)                                 # q2 = bright_3
    g("cx", tau0, 11)                             # q11 = t1
    flag(1, 10, tau0)                             # tau0 = bright_0
    g("cx", 5, 8)                                 # q8 = t2
    frame(3, 6, 5, 8)                             # corner 2: j_r raw on q5
    flag(3, 6, 8)                                 # q8 = bright_2 in place (t2 is re-read from the outer bits in the walk)
    g("rccx", 2, 8, pb)
    frame(0, 4, 5, 11)                            # corner 1: control j_r (the frame also works with j_B)
    flag(0, 4, 11)                                # q11 = bright_1

    for name, qs in fwd:
        getattr(rec, name)(*qs)

    # exp(-i beta kappa(pa, pb, z, t2) X_F) as an exact 9-term Walsh phase polynomial on F = j_r in its X basis;
    # pa = b0 & b1 is never stored: its two toggles are rccx(tau0, q11, F), residual (-1)^(b0 z) fixed by one CZ
    F = 5
    idx = {"pa": 0, "pb": 1, "z": 2, "t": 3}
    reg = {"pb": pb, "z": z}
    coef = _mux_terms()
    seq = ["t", "pb", "pa", "pb", "z", "pb", "pa", "pb+t", "z"]
    rec.h(F)
    rec.rz(2.0 * spec.beta * coef[(0, 0, 0, 0)], F)
    cur = [0, 0, 0, 0]
    for k, step in enumerate(seq):
        for v in step.split("+"):
            if v == "pa":
                rec.rccx(tau0, 11, F)
            elif v == "t":
                rec.cx(21, F); rec.cx(23, F)                 # t2 = q_j(o4) ^ q_j(o5) (Gauss law at corner 2)
            else:
                rec.cx(reg[v], F)
            cur[idx[v]] ^= 1
        if k < len(seq) - 1:
            rec.rz(2.0 * spec.beta * coef[tuple(cur)], F)
    if any(cur):
        raise RuntimeError("walk not closed")
    rec.h(F)
    rec.cz(tau0, z)

    for name, qs in reversed(fwd):
        getattr(rec, _INV.get(name, name))(*qs)
    for name, *qs in reversed(REL):
        getattr(rec, name)(*qs)
    _emit(b, rec.ops)
    b.free([tau0, z]); b.free([pb])
    return b
