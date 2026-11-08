"""SUMMARY: parent circuit unchanged in every gate that costs CX or T (dimer frame, pivot b; flag a1=[c0=c2=0], A=[u=v=0] XORed into c0; 13-toggle all-linear H-frame walk over c1, c3, c0^A, a1, e; 31 CX, 17 qubits, T 1062), with the pivot critical path shortened: each exact phase fix p(-m*pi/4) is one gate (tdg/sdg instead of z s t / z s), the electric phase of b drops its X-frame sandwich (sg=+1 form, 154-gate word plus one tdg), and the per-rotation (sign, pi/4-shift) forms plus pivot X flips are chosen by a DP over the walk for minimal word+fix+flip length at minimal T (walk chain 2010 -> 2004 gates).
DISCOVERY: the fused start block CX(0,2)CX(0,3)H(0) absorbs 14 of the 168 linear maps on (q0,q2,q3) at no CX (optimal 3-qubit Clifford synthesis), among them copying the pivot into q3 (q3 = e^p, a second rotation accumulator) and the relabel v^e; yet exhaustive two-accumulator DFS (pivot and q3 both carry p, free ends on both) finds no 12-CX walk for atoms {c0^A, a1, c1, c3}, and the three-AND designs (A + any corner-NOR pairing, A in an ancilla or any corner, atoms allowed as extra accumulators) have no 7-CX walk, so 31 CX stands.
DISCOVERY: the 19 remaining adjacent-pair direct-rccx NOR designs (12 linear toggles) and all 30 feasible 'corner NOR XORed into u/v/e with A rebuilt' designs (12-toggle budget) have no walk; no 4-rccx flag program that restores every register on the 39 configs reaches 3 independent nonlinear values (meet-in-the-middle over 88240 two-gate states), while 5-rccx programs do (4954 value sets, 160 with A and a Z/CZ-fixable leftover phase) - their segmented walks (9-10 CX for 30-31 CX total) are the open lead.
"""
FAMILY = "F1"
PARENT = "r03-F1-003"

import math
from fractions import Fraction

from su2plaq.compress.builder import Builder

PI4 = math.pi / 4
# Pivot phase walk in the H frame of qubit 0 (dimer frame: q0 = b, q1 = r^l, q2 = t^b, q3 = l^b), as in the parent.
WALK = [("start", Fraction(1, 2)), ("c1", Fraction(-1, 4)), ("a1", Fraction(1, 4)), ("c3", Fraction(-1, 8)),
        ("Ac0", Fraction(-3, 8)), ("a1", Fraction(3, 8)), ("Ac0", Fraction(1, 8)), ("c1", Fraction(-1, 4)),
        ("a1", Fraction(1, 4)), ("c3", Fraction(-1, 8)), ("Ac0", Fraction(-3, 8)), ("a1", Fraction(0)),
        ("e", Fraction(3, 8)), ("Ac0", Fraction(-3, 8))]
# Per-rotation emitted form (sg, m): angle sg*|theta| + m*pi/4, then the exact phase p(-m*pi/4); sg = -1 via an X frame
# flip of the pivot.  Chosen offline by a DP over this walk (minimal pygridsynth T first, then word + fix + flip gates).
WFORM = [(1, 0), (-1, 3), (1, 5), (1, 0), (-1, 0), (1, 0), (1, 0), (-1, 3), (1, 5), (1, 0), (-1, 0), (1, 0), (-1, 0)]
E_FORM = (1, 1)           # electric p(-3 alpha/4): p(-3 alpha/4 + pi/4) tdg, no X sandwich
FIX = {0: (), 1: ("t",), 2: ("s",), 3: ("s", "t"), 4: ("z",), 5: ("z", "t"), 6: ("sdg",), 7: ("tdg",)}


def phase_fix(b, m, q):
    """exact p(-m*pi/4) on qubit q, one Clifford+T gate where possible (one t/tdg iff m odd)."""
    for g in FIX[(-m) % 8]:
        getattr(b, g)(q)


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
    k = 0
    for g, c in WALK:
        if g != "start":
            b.cx(src[g], 0)
        if c != 0:
            sg, m = WFORM[k]
            k += 1
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
