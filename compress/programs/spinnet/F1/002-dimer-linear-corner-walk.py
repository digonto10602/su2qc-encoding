"""SUMMARY: dimer frame (pivot = link b) with one clean flag a1=[c0=c2=0] and A=[u=v=0] XORed in place into corner qubit c0; corners c1, c3 and c0^A enter the H-frame pivot walk as plain CX toggles, so the walk is all-linear (13 CX, no rccx on the pivot, no sign fix) and ends on the e-step merged into the inverse ladder; 31 CX, 13+4 rotations, 17 qubits, all angles k*beta/4 or 3*alpha/4.
DISCOVERY: with only the flags A and a1=[c0=c2=0], the raw corner parities c1, c3 complete the bright projector: the pivot polynomial over (e, A, a1, c1, c3) needs 12 terms (MILP) and an all-linear 13-toggle walk p -> p^e exists (C DFS), so the a2 rccx pair and its CZ are not needed (31 vs 32 CX); DFS finds no all-linear 12-toggle walk for any of the six corner-pair flags with A, e, u, v.
DISCOVERY: A can live in corner qubit c0 (c0 ^= A by an rccx on the non-clean target, its phase cancels with the mirrored uncompute) because c0 is read only by the a1 flag, which is computed before and uncomputed after; the walk over (e, c0^A, a1, c1, c3) still has 12-term supports and 13-toggle walks (with c2^A it needs more), so one ancilla is saved at equal CX.
"""
FAMILY = "F1"
PARENT = "r01-F1-001"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Pivot phase walk in the H frame of qubit 0 (dimer frame: q0 = b, q1 = r^l, q2 = t^b, q3 = l^b).
# Each step toggles one control onto the pivot (CX), then rotates rz(2*c*beta) on the parity reached.
# Toggles: 'a1' = flag [c0=c2=0], 'Ac0' = corner qubit 4 holding c0^A (A = [u=v=0] XORed in place),
# 'c1'/'c3' = corner qubits 5/7, 'e' = q3.
WALK = [("start", Fraction(1, 2)), ("c1", Fraction(-1, 4)), ("a1", Fraction(1, 4)), ("c3", Fraction(-1, 8)),
        ("Ac0", Fraction(-3, 8)), ("a1", Fraction(3, 8)), ("Ac0", Fraction(1, 8)), ("c1", Fraction(-1, 4)),
        ("a1", Fraction(1, 4)), ("c3", Fraction(-1, 8)), ("Ac0", Fraction(-3, 8)), ("a1", Fraction(0)),
        ("e", Fraction(3, 8)), ("Ac0", Fraction(-3, 8))]


def build(spec):
    b = Builder(spec)
    (a1,) = b.alloc(1, "flag")
    src = {"a1": a1, "Ac0": 4, "c1": 5, "c3": 7, "e": 3}
    for q in range(4):
        b.p(-0.75 * spec.alpha, q)
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
    for g, c in WALK:
        if g != "start":
            b.cx(src[g], 0)
        if c != 0:
            b.rz(float(2 * c) * spec.beta, 0)
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
