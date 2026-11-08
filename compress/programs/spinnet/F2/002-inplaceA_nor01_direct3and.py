"""SUMMARY: F2 with one ancilla: dimer ladder (pivot = link b), flag a01=[c0=c1=0] on the only ancilla, A=[u=v=0] XORed in place into the idle corner qubit c1 (X = c1^A), the 3-AND D=a01&~c3 toggled straight onto the pivot by an rccx pair, and a 10-state pivot walk over (e, X, D, c2) with 9 rotations (first step fused with the ladder, one CZ for the pair's leftover sign); rotation signs set by free pivot X-flips to shorten the Clifford+T words; 32 CX, 13 rotations, 17 qubits, angles k*beta/4 and -3*alpha/4.
DISCOVERY: a flag used only as an rccx control frees its own input qubits between compute and uncompute: with a01=[c0=c1=0] feeding the pivot rccx D=a01&~c3, c1 is idle during the walk and can carry A in place (X=c1^A); the walk over (e, X, D, c2) still needs only 9 terms, so the F1 cost (32 CX, T 832) is reached with 17 qubits instead of 18.
DISCOVERY: the pivot X-frame parity is free to choose per rotation (X on the pivot commutes with every CX toggle, costs a Z on the first control of an rccx it straddles, and at the walk ends turns into a Z on b next to the frame H); flipping rz(-beta/4) to rz(+beta/4) shortens its pygridsynth word from 167 to 140 gates, depth_CT 1583 -> 1554 at equal T.
DISCOVERY: walk search (MILP enumeration of up to 30-300 minimal term sets per atom set + Dijkstra with exact rccx-pair leftover-sign costs and the dark relations c1*e=0, c0*(e^v)=0, c2*(e^u)=0, c3*(e^u^v)=0) over ~150 atom sets with three AND units (two NOR pairs, NOR pair + 3-AND through it, A in place or as ancilla, extra u/v wires) never went below 32 CX = 6 ladder + 18 (three rccx pairs) + 7 linear toggles + 1 sign fix; two corner-shifted NOR flags replacing three AND units need >= 22 CX of flags.
"""
import numpy as np

from su2plaq.compress.builder import Builder

FAMILY = "F2"
PARENT = "r01-F2-001"

CORNER_LINKS = {0: (0, 3), 1: (0, 1), 2: (1, 2), 3: (2, 3)}   # corner c_k touches links (b r t l = 0 1 2 3)
NAMES = ["e", "X", "D", "c2"]       # walk atoms: e = b^r (q1), X = c1^A (q5, in place), D = a01&~c3 (rccx on pivot), c2 (q6)
START = "e"                         # first walk state, produced by the fused ladder Clifford
WALK = ["X", "e", "c2", "X", "D", "X", "c2", "X", "D"]       # toggles onto the pivot after the start
PAR = {"e", "e.X", "X.c2", "c2", "1"}                         # rotations emitted in the X-flipped pivot frame


def _kappa(y):
    """Bright-pair coupling K(y <-> y^1111) (Lean couplings_2k: 2K = -4, -1, +2)."""
    z = [(y >> i) & 1 for i in range(4)]
    if len(set(z)) == 1:
        return -2.0
    if z[0] == z[2] and z[1] == z[3]:
        return -0.5
    return 1.0


def _atoms(y, c):
    b = [(y >> i) & 1 for i in range(4)]
    cc = [(c >> k) & 1 for k in range(4)]
    u, v = b[0] ^ b[2], b[1] ^ b[3]
    A = int(u == 0 and v == 0)
    a01 = int(cc[0] == 0 and cc[1] == 0)
    return {"e": b[0] ^ b[1], "X": cc[1] ^ A, "D": a01 & (1 - cc[3]), "c2": cc[2]}


def _mask(name):
    bit = {n: 1 << i for i, n in enumerate(NAMES)}
    return 0 if name == "1" else sum(bit[n] for n in name.split("."))


def _name(x):
    return ".".join(n for i, n in enumerate(NAMES) if x >> i & 1) or "1"


def _states():
    x = _mask(START)
    out = [x]
    for g in WALK:
        x ^= _mask(g)
        out.append(x)
    assert x == 0
    return out


def _coeffs(terms):
    """Pivot polynomial f = sum_T a_T Z_T over the walk states: f = K on bright codes, 0 on dark codes (corner rule)."""
    rows = {}
    for c in range(16):
        need = set().union(*[CORNER_LINKS[k] for k in range(4) if c >> k & 1]) if c else set()
        for y in range(16):
            if not all(y >> l & 1 for l in need):
                continue
            at = _atoms(y, c)
            key = sum(at[n] << i for i, n in enumerate(NAMES))
            fv = _kappa(y) if c == 0 else 0.0
            assert rows.get(key, fv) == fv
            rows[key] = fv
    keys = sorted(rows)
    W = np.array([[(-1) ** bin(k & t).count("1") for t in terms] for k in keys], float)
    f = np.array([rows[k] for k in keys])
    a, *_ = np.linalg.lstsq(W, f, rcond=None)
    assert np.abs(W @ a - f).max() < 1e-12
    k = np.round(a * 8)
    assert np.abs(a * 8 - k).max() < 1e-9          # exact multiples of 1/8 (rotation angles k*beta/4)
    return {t: float(x) / 8 for t, x in zip(terms, k)}


def build(spec):
    st = _states()
    co = _coeffs(sorted(set(st)))
    b = Builder(spec)
    (a01,) = b.alloc(1, "a01")
    par = [int(_name(st[0]) in PAR)]
    if par[0]:
        b.z(0)                              # = X on the pivot right after the frame H (Z commutes with the CX controls)
    for q in range(4):                      # U_E: -3/4 alpha per j=1/2 inner link
        b.p(-0.75 * spec.alpha, q)
    b.x(4); b.x(5)
    b.rccx(4, 5, a01)                       # a01 = [c0=0][c1=0]
    b.x(5)
    b.cx(0, 2)                              # u = b^t on q2
    b.cx(1, 3)                              # v = r^l on q3
    b.x(2); b.x(3)
    b.rccx(2, 3, 5)                         # c1 ^= A = [u=0][v=0]  (c1 is idle until a01 is uncomputed)
    b.sdg(1); b.cx(0, 1); b.s(1); b.s(0); b.h(0)   # = CX(0->1) H(0) CX(1->0): e = b^r on q1, pivot starts at state e
    b.x(7)                                  # ~c3 for the D rccx
    done = set()

    def rot(x):
        if abs(co.get(x, 0.0)) > 0 and x not in done:
            done.add(x)
            p = int(_name(x) in PAR)
            if p != par[0]:
                b.x(0); par[0] = p
            b.rz((-1) ** par[0] * 2.0 * co[x] * spec.beta, 0)

    rot(st[0])
    wire = {"e": 1, "X": 5, "c2": 6}
    for i, g in enumerate(WALK):
        if g == "D":
            b.rccx(a01, 7, 0)               # pivot ^= a01 & ~c3
            if par[0]:
                b.z(a01)                    # X-flipped pivot: X rccx X = Z(first control) rccx
        else:
            b.cx(wire[g], 0)
        rot(st[i + 1])
    assert done == {s for s in co if co[s] != 0}
    b.cz(a01, 6)                            # leftover sign (-1)^(a01 * c2) of the D pair (c2 toggled once between them)
    b.x(7)
    b.h(0)
    b.cx(0, 1)
    b.rccx(2, 3, 5)                         # c1 ^= A
    b.x(3); b.x(2)
    b.x(5)
    b.rccx(4, 5, a01)                       # uncompute a01
    b.x(5); b.x(4)
    b.free([a01])
    b.cx(1, 3)
    b.cx(0, 2)
    if par[0]:
        b.z(0)                              # = X on the pivot right before the frame H
    return b
