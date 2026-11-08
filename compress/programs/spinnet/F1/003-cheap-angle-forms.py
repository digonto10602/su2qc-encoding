"""SUMMARY: parent circuit unchanged in gates that cost CX (dimer frame, pivot b; flag a1=[c0=c2=0], A=[u=v=0] XORed into c0; 13-toggle all-linear H-frame walk over c1, c3, c0^A, a1, e; 31 CX, 17 qubits), but every rotation is emitted in its cheapest exact Clifford+T-equivalent form sg*|th| + m*pi/4 followed by p(-m*pi/4): the 4 electric p(-3alpha/4) and the 4 rz(+-beta/2) take a pi/4 shift (pygridsynth T 64 -> 58+1, 66 -> 64+1), signs ride on X frame flips (pivot or link qubit) and pi/2 shifts on S/Z fixes, picked for the shortest word; T 1086 -> 1062, depth_CT 2258 -> 2189.
DISCOVERY: pygridsynth T (eps=1e-6) of rz(th) is unchanged by th -> -th and th -> th + pi/2 but not by th -> th + pi/4, and rz(th) = rz(th + pi/4) tdg exactly, so each rotation costs min(T(th), T(th + pi/4) + 1): -3alpha/4 drops 64 -> 59 and beta/2 66 -> 65 (24 T at zero CX); sign flips (X on the pivot commutes with every toggle CX(g -> pivot)) and pi/2 shifts keep T and only shorten words (depth_CT -69).
DISCOVERY: no 30-CX walk in the two-AND F1 space: exact walk DFS (free ends span(e, v) via the 2-CX merged block CX(0,2)CX(0,3)H(0)CX(2,0)CX(3,0), after which q2 = v, q3 = e stay readable) over 150 designs (corner NOR N_ij and A, each in an ancilla or XORed into a corner, e or the other flag, both orders, all qubits toggles; MILP >= 12 terms each) finds no 12-toggle walk, nor do the 10 diagonal-NOR direct-rccx-pair designs at 12 linear toggles; 13-toggle walks exist only for the parent register set (also with u, v or c2 added) and all keep 13 rotations.
"""
FAMILY = "F1"
PARENT = "r02-F1-002"

import math
from fractions import Fraction

from su2plaq.compress.builder import Builder

PI4 = math.pi / 4
# Pivot phase walk in the H frame of qubit 0 (dimer frame: q0 = b, q1 = r^l, q2 = t^b, q3 = l^b), as in the parent.
WALK = [("start", Fraction(1, 2)), ("c1", Fraction(-1, 4)), ("a1", Fraction(1, 4)), ("c3", Fraction(-1, 8)),
        ("Ac0", Fraction(-3, 8)), ("a1", Fraction(3, 8)), ("Ac0", Fraction(1, 8)), ("c1", Fraction(-1, 4)),
        ("a1", Fraction(1, 4)), ("c3", Fraction(-1, 8)), ("Ac0", Fraction(-3, 8)), ("a1", Fraction(0)),
        ("e", Fraction(3, 8)), ("Ac0", Fraction(-3, 8))]
# Cheapest equivalent form per |coefficient| (fixed offline from pygridsynth T, then word length, at eps=1e-6):
# emitted angle = sg*|theta| + m*pi/4, followed by the exact phase p(-m*pi/4); sg = -1 is realised by an X frame flip.
FORM = {Fraction(1, 2): (1, 0), Fraction(1, 4): (1, 5), Fraction(1, 8): (1, 0), Fraction(3, 8): (-1, 0)}
E_FORM = (-1, 1)          # electric p(-3 alpha/4): X p(3 alpha/4 + pi/4) tdg X


def phase_fix(b, m, q):
    """exact p(-m*pi/4) on qubit q with Clifford+T gates (one t/tdg iff m odd)."""
    m = (-m) % 8
    if m & 4:
        b.z(q)
    if m & 2:
        b.s(q)
    if m & 1:
        b.t(q)


def build(spec):
    b = Builder(spec)
    (a1,) = b.alloc(1, "flag")
    src = {"a1": a1, "Ac0": 4, "c1": 5, "c3": 7, "e": 3}
    sg, m = E_FORM
    for q in range(4):                       # U_E: p(-3 alpha/4) on every link
        lam = -0.75 * spec.alpha
        if sg < 0:
            b.x(q)
        b.p(sg * lam + m * PI4, q)
        phase_fix(b, m, q)
        if sg < 0:
            b.x(q)
    b.cx(3, 1)
    b.cx(0, 2)
    b.cx(0, 3)
    b.x(4)
    b.x(6)
    b.rccx(4, 6, a1)          # a1 = [c0 = 0][c2 = 0]
    b.x(4)
    b.x(1)
    b.x(2)
    b.rccx(1, 2, 4)           # c0 ^= A, A = [u = 0][v = 0]
    b.h(0)
    flip = False              # X frame of the pivot: X rz(t) X = rz(-t), X commutes with every toggle CX(g -> 0)
    for g, c in WALK:
        if g != "start":
            b.cx(src[g], 0)
        if c != 0:
            sg, m = FORM[abs(c)]
            want = (c < 0) != (sg < 0)
            if want != flip:
                b.x(0)
                flip = want
            b.rz(sg * float(2 * abs(c)) * spec.beta + m * PI4, 0)
            phase_fix(b, m, 0)
    if flip:
        b.x(0)
    b.h(0)
    b.sdg(0)
    b.sdg(3)
    b.cx(0, 3)
    b.s(3)
    b.rccx(1, 2, 4)
    b.x(1)
    b.x(2)
    b.x(4)
    b.rccx(4, 6, a1)
    b.x(4)
    b.x(6)
    b.free([a1])
    b.cx(0, 2)
    b.cx(3, 1)
    return b
