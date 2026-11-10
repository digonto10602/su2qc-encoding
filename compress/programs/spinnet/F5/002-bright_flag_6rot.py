"""SUMMARY: T-lean step with 10 rotations at 34 CX: U_E = 4 link phases; U_B = 6-term pivot polynomial f = 1/8 + 3/8 Z_F + 1/4 Z_B - 3/4 Z_F Z_B - 3/8 Z_e + 3/8 Z_F Z_e in the dimer frame, B = bright = (c1^X)&Y toggled by a direct rccx pair (X = NOR(c0,c2) XORed into c1, Y = NOR(c1,c3) in one ancilla), F = c0^A (A = [u=v=0] XORed into c0); walk [e] F e B F B (fused start) + one CZ for the rccx-pair sign; 17 qubits, angles k*beta/4 and -3*alpha/4.
DISCOVERY: with the bright flag B available as a toggle, U_B needs only 6 terms {1, A, B, AB, e, Ae} (minimal over gens A,B,e,u,v); the best walk is [e] A e B A B = 9 pivot CX + 1 CZ (the B pair encloses one A toggle, sign (-1)^(x*A)), and an exhaustive search (all 6-7 term supports, shifts by span(X,Y), CX among pivot/flag/e, free ends in span(e,v)) finds nothing below 10, so 6 ladder + 18 flag + 10 = 34 CX is this family's floor.
DISCOVERY: toggling both A and B by direct rccx pairs (31 CX) forces interleaved pairs whose leftover sign l1*X*(Y^l2) is 3-body on the valid codes; no choice of literals, corner pairing, first controls or walk (<= 3 extra cheap toggles) makes it fixable with <= 2 CZ, nor do control-order swaps of in-place uncomputes (they only give (l1^l2)*t0).
DISCOVERY: in-place flags are exact: (c1 ^ NOR(c0,c2)) & NOR(c1,c3) = NOR4 because Y=1 forces c1=0, and F = c0 ^ A may replace A since F*e = 0 on every dark code (c0=1 => b=l=1 => e=0); two in-place rccx among the corner qubits can never give NOR4 as an AND of two literals (exhaustive), so one ancilla remains.
"""
FAMILY = "F5"
PARENT = "r01-F5-001"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Pivot walk in the H frame of qubit 0 (dimer frame: q0 = b, q1 = u = r^l, q2 = v = t^b, q3 = e = l^b).
# Node -> coefficient c (units of beta) of the term Z_P (-1)^node; each node is rotated rz(2 c beta) once.
# f = sum c (-1)^node equals K on the 8 bright pairs (kappa = 1, -2 for 0000/1111, -1/2 for 0101/1010) and 0 on
# all 31 dark codes (there Z_B = 1 and f = 3/8 (1 - Z_F)(1 - Z_e) = 3/2 F e = 0).
COEF = {"e": Fraction(-3, 8), "eF": Fraction(3, 8), "F": Fraction(3, 8), "FB": Fraction(-3, 4),
        "B": Fraction(1, 4), "1": Fraction(1, 8)}


def build(spec):
    b = Builder(spec)
    (y,) = b.alloc(1, "flagY")
    beta = spec.beta
    # ---- U_E: exp(-i 3/4 alpha) per link j = 1/2
    for q in range(4):
        b.p(-0.75 * spec.alpha, q)
    # ---- corner flags: y = NOR(c1,c3); q5 = c1 ^ NOR(c0,c2)  (so q5 & y = B, the bright indicator)
    b.x(5); b.x(7)
    b.rccx(5, 7, y)
    b.x(5)
    b.x(4); b.x(6)
    b.rccx(4, 6, 5)
    b.x(4)
    # ---- dimer ladder (q1 = r^l, q2 = t^b) and q4 = F = c0 ^ A with A = NOR(u, v)
    b.cx(3, 1)
    b.cx(0, 2)
    b.x(1); b.x(2)
    b.rccx(1, 2, 4)
    # ---- cx(0,3) h(0) cx(3,0) as one 1-CX Clifford: last ladder CX + pivot preload of e
    b.sdg(3); b.cx(0, 3); b.s(3); b.s(0); b.h(0)

    def rot(k):
        b.rz(float(2 * COEF[k]) * beta, 0)

    rot("e")
    b.cx(4, 0); rot("eF")
    b.cx(3, 0); rot("F")
    b.rccx(5, y, 0); rot("FB")
    b.cx(4, 0); rot("B")
    b.rccx(5, y, 0); rot("1")
    b.cz(5, 4)                    # sign (-1)^(q5 * q4) left by the B rccx pair around the F toggle
    # ---- uncompute flags
    b.rccx(1, 2, 4)
    b.x(1); b.x(2)
    b.x(4)
    b.rccx(4, 6, 5)
    b.x(5)
    b.rccx(5, 7, y)
    b.x(4); b.x(5); b.x(6); b.x(7)
    b.free([y])
    # ---- leave the pivot frame
    b.h(0)
    b.cx(0, 3)
    b.cx(0, 2)
    b.cx(3, 1)
    return b
