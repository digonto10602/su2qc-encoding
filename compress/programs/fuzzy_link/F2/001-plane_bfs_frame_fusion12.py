"""SUMMARY: frame and parity network fused into one 12-CX Clifford path found by meet-in-the-middle BFS over 4-qubit Clifford cosets modulo single-qubit Cliffords (each qubit = one hyperbolic plane of Paulis); the 10 commuting Pauli rotations (6 at +-alpha/4, 4 at +-2 kappa2) are applied whenever a plane contains a target Pauli; 12 CX, 10 rotations.
DISCOVERY: with single-qubit Cliffords free, a 4-qubit Clifford coset is a tuple of 4 mutually orthogonal hyperbolic planes in F2^8 and each CX (with locals) has exactly 9 outcomes per qubit pair; an rz is available exactly on the nonzero elements of a plane, so the UE target needs only a path of planes I->I whose planes jointly contain the 10 Z-strings of V=<X1X3,Z1Z3,X2X4,Z2Z4>.
DISCOVERY: in that model (all intermediate cosets either diagonalise V on every qubit or are within 3 CX of identity) the minimum is 12 CX (no 10- or 11-CX path; search scratch/proposer/fl_gen.py), one below the Bell-frame + I->I network 2+9+2=13.
"""
FAMILY = "F2"
PARENT = "r01-F1-001"

from su2plaq.compress.builder import Builder

# Gate list (qubits 0..3 = q4, q3, q2, q1); ('rz', q, ca, ck) means rz(ca*alpha + ck*kappa2) on q.
GATES = [
    ('h', 0), ('h', 2), ('cx', 0, 2), ('h', 0),
    ('rz', 0, -0.25, 0.0), ('rz', 2, -0.25, 0.0),
    ('cx', 0, 1), ('h', 1), ('s', 3), ('cx', 1, 3), ('s', 1), ('h', 1),
    ('rz', 1, 0.0, -2.0), ('s', 3), ('h', 3), ('rz', 3, 0.0, 2.0),
    ('h', 1), ('h', 2), ('cx', 1, 2), ('h', 1), ('rz', 1, 0.0, -2.0),
    ('h', 1), ('h', 3), ('cx', 1, 3), ('h', 1), ('rz', 1, 0.25, 0.0),
    ('h', 1), ('cx', 1, 2), ('h', 1), ('rz', 1, 0.25, 0.0),
    ('h', 0), ('cx', 0, 2), ('h', 0), ('rz', 0, -0.25, 0.0),
    ('cx', 0, 1), ('rz', 1, 0.25, 0.0),
    ('h', 1), ('cx', 1, 3), ('h', 1), ('rz', 1, 0.0, -2.0),
    ('h', 1), ('s', 3), ('cx', 1, 3), ('cx', 1, 2),
    ('h', 0), ('s', 2), ('cx', 0, 2), ('s', 0), ('h', 0),
    ('s', 1), ('h', 1), ('s', 2), ('s', 3), ('x', 0), ('z', 2),
]


def build(spec):
    b = Builder(spec)
    a, k2 = spec.alpha, spec.beta
    for g in GATES:
        op = g[0]
        if op == 'cx':
            b.cx(g[1], g[2])
        elif op == 'rz':
            b.rz(g[2] * a + g[3] * k2, g[1])
        else:
            getattr(b, op)(g[1])
    return b
