"""SUMMARY: F2 single-flag corner polynomial: dimer ladder (pivot = link b), one rccx flag A=[u=v=0], and a 22-step closed pivot walk over the raw corner parities (c0..c3, A, e) carrying 18 rz(+-beta/4) terms; the first walk step is fused with the last ladder CX into a 1-CX Clifford; 33 CX, 17 qubits, all angles +-beta/4 or -3*alpha/4.
DISCOVERY: CX(b->r); H(b); CX(r->b) is a 1-CX Clifford, so a pivot walk that starts or ends with the e-step saves 1 CX per fused end; with the A flag alone, exhaustive IDA* over the 624 minimal 16-term corner sets (<= 5 relabel CX among c0..c3,A,e) shows the walk costs >= 21 CX after fusion, i.e. >= 33 CX in total; annealing over non-minimal term sets also stops at 21 (18-19 terms).
DISCOVERY: Every minimal 16-term solution over (c,A,e) has rotation +-beta/4 per corner subset T and decoration g_A = NOT 1_H(T), g_e = 1_H xor 1_K, where H, K are 4-sets of corner subsets balanced on the dark zero sets {c0,c1,c2,c3,c0c1,c1c2} resp. {c0,c2,c3,c2c3,c0c3} with |H & K| = 1; H can never be a face of the corner 4-cube, so every Gray walk pays about 6 decoration toggles.
DISCOVERY: Dropping the A flag (terms over c0..c3,e,u,v) does not pay: 16 terms are infeasible (MILP), the best support found has 22 terms and annealed pivot walks need >= 30 CX (36 total).
"""

import numpy as np
from su2plaq.compress.builder import Builder

FAMILY = "F2"
PARENT = None

NAMES = ['c0', 'c1', 'c2', 'c3', 'A', 'e']          # control wires of the pivot walk (bit i of a parity label = NAMES[i])
MOVES = [('p', 5), ('p', 2), ('p', 1), ('p', 0), ('p', 4), ('p', 3), ('p', 2), ('p', 4), ('p', 1), ('p', 0), ('p', 4), ('p', 5), ('p', 1), ('p', 2), ('p', 1), ('p', 0), ('p', 3), ('p', 2), ('p', 1), ('p', 0), ('p', 1), ('p', 4)]          # ("p", w): CX(NAMES[w] -> pivot); ("f", a, b): relabel CX(NAMES[a] -> NAMES[b])
TERMS = [0, 16, 17, 18, 19, 21, 26, 28, 29, 30, 32, 36, 38, 41, 43, 55, 56, 63]          # parities (besides the pivot) that carry a rotation
CORNER_LINKS = {0: (0, 3), 1: (0, 1), 2: (1, 2), 3: (2, 3)}   # corner c_k touches links (b r t l = 0 1 2 3)


def _kappa(y):
    """Bright-pair coupling K(y <-> y^1111) in units of 1 (Lean: couplings_2k = -4, -1, +2)."""
    z = [(y >> i) & 1 for i in range(4)]
    if len(set(z)) == 1:
        return -2.0
    if z[0] == z[2] and z[1] == z[3]:
        return -0.5
    return 1.0


def _rows():
    """Pivot-angle function f on every valid data code: f = K on bright codes, 0 on dark codes (corner rule)."""
    rows = {}
    for c in range(16):
        need = set().union(*[CORNER_LINKS[k] for k in range(4) if c >> k & 1]) if c else set()
        for y in range(16):
            if not all(y >> l & 1 for l in need):
                continue
            b = [(y >> i) & 1 for i in range(4)]
            val = dict(e=b[0] ^ b[1], u=b[0] ^ b[2], v=b[1] ^ b[3])
            val["A"] = int(val["u"] == 0 and val["v"] == 0)
            for k in range(4):
                val["c%d" % k] = c >> k & 1
            key = sum(val[n] << i for i, n in enumerate(NAMES))
            fv = _kappa(y) if c == 0 else 0.0
            assert rows.get(key, fv) == fv
            rows[key] = fv
    return rows


def _coeffs():
    rows = _rows()
    keys = sorted(rows)
    W = np.array([[(-1) ** bin(k & t).count("1") for t in TERMS] for k in keys], float)
    f = np.array([rows[k] for k in keys])
    a, *_ = np.linalg.lstsq(W, f, rcond=None)
    assert np.abs(W @ a - f).max() < 1e-12
    return {t: float(x) for t, x in zip(TERMS, a)}


def build(spec):
    co = _coeffs()
    b = Builder(spec)
    wire = {"e": 1, "u": 2, "v": 3, "c0": 4, "c1": 5, "c2": 6, "c3": 7}
    useA = "A" in NAMES
    if useA:
        (anc,) = b.alloc(1, "A")
        wire["A"] = anc
    W = [wire[n] for n in NAMES]
    e_idx = NAMES.index("e")
    m_start = MOVES[0] == ("p", e_idx)
    m_end = MOVES[-1] == ("p", e_idx)
    for q in range(4):                       # U_E: -arg(U_E)/alpha = 3/4 * (number of j=1/2 inner links)
        b.p(-0.75 * spec.alpha, q)
    b.cx(0, 2)                               # u = b ^ t
    b.cx(1, 3)                               # v = r ^ l
    if useA:                                 # A = [u = 0][v = 0]
        b.x(2); b.x(3); b.rccx(2, 3, anc)
    basis = [1 << i for i in range(len(NAMES))]
    x = 0
    done = set()

    def rot():
        if x in co and x not in done:
            done.add(x)
            b.rz(2.0 * co[x] * spec.beta, 0)
    if m_start:                              # CX(0->1); H(0); CX(1->0) as one CX
        b.z(0); b.h(1); b.s(1); b.cx(0, 1); b.sdg(0); b.h(0); b.sdg(1); b.h(1)
        x ^= basis[e_idx]
        rot()
    else:
        b.cx(0, 1); b.h(0)                   # e = b ^ r; pivot X^{(x)4} -> X_0 -> Z_0
        rot()
    n = len(MOVES)
    for i, m in enumerate(MOVES):
        if (i == 0 and m_start):
            continue
        if i == n - 1 and m_end:
            x ^= basis[m[1]]
            b.x(0); b.h(0); b.s(0); b.h(1); b.s(1); b.cx(0, 1); b.sdg(1); b.h(1)   # CX(1->0); H(0); CX(0->1)
            continue
        if m[0] == "p":
            b.cx(W[m[1]], 0)
            x ^= basis[m[1]]
            rot()
        else:
            b.cx(W[m[1]], W[m[2]])
            basis[m[2]] ^= basis[m[1]]
    assert x == 0 and basis == [1 << i for i in range(len(NAMES))] and done == set(co), (x, sorted(set(co) - done))
    if not m_end:
        b.h(0); b.cx(0, 1)
    if useA:
        b.rccx(2, 3, anc); b.x(3); b.x(2)
    b.cx(1, 3)
    b.cx(0, 2)
    return b
