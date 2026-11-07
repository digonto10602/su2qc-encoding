"""SUMMARY: dimer frame (pivot = link b) with two clean flags a1=[c0=c2=0], A=[u=v=0] and the third AND a2=[c1=c3=0] toggled straight onto the pivot by two rccx inside the H-frame phase walk (one CZ cancels their leftover sign), plus a 1-CX merge of the last ladder CX with the first walk toggle; 32 CX, 9+4 rotations, all angles k*beta/4 or 3*alpha/4.
DISCOVERY: two rccx gates targeting the walk pivot leave only the sign (-1)^(l1*dS) (l1 = their first control, dS = parity toggled on the pivot between them), so an AND toggled twice costs 6 CX instead of 6+2 with an ancilla; here dS = a1 and one CZ(c1bar, a1) removes it.
DISCOVERY: CX(a->b) H(a) CX(b->a) = sdg(b) CX(a->b) s(b) s(a) h(a) (1 CX), so the ladder's last CX merges with the first pivot toggle when the walk starts with that ladder qubit and the constant term is rotated at the end of the walk.
"""
FAMILY = "F1"
PARENT = None

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Pivot phase walk in the H frame of qubit 0 (dimer frame: q0 = b, q1 = r^l, q2 = t^b, q3 = l^b).
# Each step toggles one control onto the pivot, then rotates rz(2*c*beta) on the parity reached.
# Toggles: 'e' = CX(q3 -> q0), 'A' = CX(flag A -> q0), 'a1' = CX(flag a1 -> q0), 'a2' = rccx(c1bar, c3bar -> q0).
# Coefficients c (units of beta) solve f = B*kappa(A, e) on the 39 valid control configurations
# (kappa = 1, -2, -1/2; f = 0 on dark codes); the first toggle 'e' is folded into the ladder (peephole) and
# the constant term (parity 0) is rotated after the last toggle.
WALK = [("e", Fraction(-3, 8)), ("A", Fraction(3, 8)), ("e", Fraction(0)), ("a1", Fraction(-3, 8)),
        ("A", Fraction(1, 8)), ("a2", Fraction(-1, 8)), ("A", Fraction(3, 8)), ("a1", Fraction(-3, 8)),
        ("A", Fraction(1, 8)), ("a2", Fraction(1, 4))]


def build(spec):
    b = Builder(spec)
    a1, fA = b.alloc(2, "flags")
    # electric layer U_E: -3/4 alpha per link j = 1/2
    for q in range(4):
        b.p(-0.75 * spec.alpha, q)
    # dimer ladder: q1 = r^l, q2 = t^b, (q3 = l^b merged below)
    b.cx(3, 1)
    b.cx(0, 2)
    # negated literals and the two clean flags
    for q in (4, 5, 6, 7, 1, 2):
        b.x(q)
    b.rccx(4, 6, a1)          # a1 = [c0 = 0][c2 = 0]
    b.rccx(1, 2, fA)          # A  = [u = 0][v = 0]
    # cx(0,3); h(0); cx(3,0)  ==  sdg(3) cx(0,3) s(3) s(0) h(0)   (first walk toggle 'e' included)
    b.sdg(3)
    b.cx(0, 3)
    b.s(3)
    b.s(0)
    b.h(0)
    for k, (g, c) in enumerate(WALK):
        if k > 0:
            if g == "e":
                b.cx(3, 0)
            elif g == "A":
                b.cx(fA, 0)
            elif g == "a1":
                b.cx(a1, 0)
            elif g == "a2":
                b.rccx(5, 7, 0)   # a2 = [c1 = 0][c3 = 0] toggled directly onto the pivot
        if c != 0:
            b.rz(float(2 * c) * spec.beta, 0)
    b.cz(5, a1)               # cancels the leftover sign (-1)^(c1bar * a1) of the rccx pair
    b.rccx(1, 2, fA)
    b.rccx(4, 6, a1)
    for q in (2, 1, 7, 6, 5, 4):
        b.x(q)
    b.free([a1, fA])
    b.h(0)
    b.cx(0, 3)
    b.cx(0, 2)
    b.cx(3, 1)
    return b
