"""SUMMARY: three-AND F1 variant with a chained direct flag: dimer frame (pivot b), clean ancillas N12=[c1=c2=0] and A=[u=v=0], and D=[c3=0]&N12 (NOR3 of c1,c2,c3) toggled straight onto the pivot by an rccx pair; the raw corner c0 completes the bright projector, so the walk A D A c0 A D e A c0 (start p, end p^e fused into the inverse ladder) carries a 9-term polynomial (angles k*beta/8) and one CZ(c3bar, c0) removes the pair's leftover sign (-1)^(c3bar*c0); 32 CX, 9+4 rotations, 18 qubits (no robust gain: CX 32 > 31).
DISCOVERY: qiskit rccx(a,b,t) is CCX times the phase i^(2ab + 4a*t_in) (units of pi/4), so a direct pair on the pivot leaves (-1)^(a*dS); emitting one gate of a pair as its T<->Tdg conjugate adds (-1)^(ab) (a free CZ between the two controls) and an X-conjugated target adds (-1)^a; in the F5-type double-direct design (A and NOR4 both direct, 31 CX) the A pair must enclose an e toggle, its sign abar*e is quadratic on the 8 bright configs, and no Z8 phase on single non-pivot wires (T/S/Z at any time) fixes it, so it needs a CZ (32 CX).
DISCOVERY: scratch searches (complete for (i),(ii); partial for (iii)) find no 31-CX design with fewer than 13 walk rotations: (i) the 8 minimal 12-term supports over (e, c0^A, a1, c1, c3) have no CX parity network of <= 13 CX even when any of 9 wires may carry the pivot variable; (ii) the 118 three-AND atom sets Z (A plus any 2-rccx program values, f a function of Z, e, v) have no walk of <= 8 toggles; (iii) of 4546 designs A + one AND (ancilla or in place) + one direct AND (incl. chained NOR3 and up to two raw-corner atoms), the first ~800 (all shared-literal ones) have cost-13 walks only with a leftover sign that is not GF(2)-linear.
DISCOVERY: NOR3(c1,c2,c3) as a direct AND of [c3=0] and the ancilla N12 plus the raw corner c0 gives 9-term walks of cost 13 (7 linear toggles + 2 rccx), the same count as the A+a1+a2 design of r01-F1-001, but every such walk encloses dS in {c0, A, c0^e, A^e}, all quadratic against the first control, so 32 CX is the floor of this design.
"""
FAMILY = "F1"
PARENT = "r04-F1-004"

from fractions import Fraction

from su2plaq.compress.builder import Builder

# Pivot walk in the H frame of qubit 0 (dimer frame: q0 = b, q1 = u = r^l, q2 = v = t^b, q3 = e = l^b).
# Each step toggles one control onto the pivot, then rz(2*c*beta) on the parity reached (c in units of beta).
# Toggles: 'A' = CX(ancilla A -> q0), 'c0' = CX(corner c0 -> q0), 'e' = CX(q3 -> q0),
# 'D' = rccx(c3bar, N12 -> q0) (D = [c3=0][c1=0][c2=0], first control c3bar).  The walk ends on p^e: that last
# e step is fused with the inverse ladder (h, sdg, sdg, cx, s), so it costs no CX.
# Coefficients: exact least-squares solution of f = B*kappa on the 39 valid control configurations
# (support 9: f = 1/8 + 3/8 A - 3/8 AD + 1/8 D + 1/8 Dc0 - 3/8 ADc0 + 3/8 Ac0e - 1/8 c0e - 1/4 e, chi = (-1)^parity).
WALK = [("start", Fraction(1, 8)), ("A", Fraction(3, 8)), ("D", Fraction(-3, 8)), ("A", Fraction(1, 8)),
        ("c0", Fraction(1, 8)), ("A", Fraction(-3, 8)), ("D", Fraction(0)), ("e", Fraction(3, 8)),
        ("A", Fraction(-1, 8)), ("c0", Fraction(-1, 4))]


def build(spec):
    b = Builder(spec)
    n12, fa = b.alloc(2, "flags")
    for q in range(4):                      # U_E: p(-3 alpha/4) on every link j = 1/2
        b.p(-0.75 * spec.alpha, q)
    b.cx(3, 1)                              # dimer ladder
    b.cx(0, 2)
    b.cx(0, 3)
    for q in (5, 6, 1, 2):
        b.x(q)
    b.rccx(5, 6, n12)                       # N12 = [c1 = 0][c2 = 0]
    b.rccx(1, 2, fa)                        # A   = [u = 0][v = 0]
    for q in (5, 6, 1, 2):
        b.x(q)
    b.h(0)
    src = {"A": fa, "c0": 4, "e": 3}
    for g, c in WALK:
        if g == "D":
            b.x(7)
            b.rccx(7, n12, 0)               # D = [c3 = 0] & N12 toggled straight onto the pivot
            b.x(7)
        elif g != "start":
            b.cx(src[g], 0)
        if c != 0:
            b.rz(float(2 * c) * spec.beta, 0)
    # leftover sign of the D pair: (-1)^(c3bar * dS) with dS = A ^ c0 ^ A = c0
    b.x(7)
    b.cz(7, 4)
    b.x(7)
    # cx(3,0) h(0) cx(0,3)  ==  h(0) sdg(0) sdg(3) cx(0,3) s(3)   (walk end p^e fused into the ladder)
    b.h(0)
    b.sdg(0)
    b.sdg(3)
    b.cx(0, 3)
    b.s(3)
    for q in (5, 6, 1, 2):
        b.x(q)
    b.rccx(1, 2, fa)
    b.rccx(5, 6, n12)
    for q in (5, 6, 1, 2):
        b.x(q)
    b.free([n12, fa])
    b.cx(0, 2)
    b.cx(3, 1)
    return b
