"""SUMMARY: pair-Bell frame cx(q1,q3) cx(q2,q4) h(q1) h(q2) (2 CX each side) around a BFS-optimal 9-CX I->I parity network carrying the 10 Z-string phases as rz(-alpha/4) (6 K1 strings) and rz(-2 kappa2) (4 K2 strings); 13 CX, 10 rotations.
DISCOVERY: in the frame (qubit bits b0..b3 after cx(3,1) cx(2,0) h(3) h(2)) H = const - alpha/8 * sum Z_s over s in {0001,0011,0100,0101,0110,0111} - kappa2 * sum Z_s over s in {1000,1011,1110,1111}; signs are constant, so every angle is -alpha/4 or -2 kappa2.
DISCOVERY: the 9-CX network cx(0,1) cx(0,2) cx(3,1) cx(2,1) cx(0,1) cx(0,2) cx(3,1) cx(0,1) cx(2,1) returns to identity and visits all 7 weight>1 parities (BFS over GL(4,2) x coverage, minimum).
"""
FAMILY = "F1"
PARENT = None

from su2plaq.compress.builder import Builder

# CX network (control, target) over qubits 0..3 = (q4, q3, q2, q1), found by BFS (scratch/proposer/fl_path.py).
NET = [(0, 1), (0, 2), (3, 1), (2, 1), (0, 1), (0, 2), (3, 1), (0, 1), (2, 1)]
K1_STRINGS = {0b0001, 0b0011, 0b0100, 0b0101, 0b0110, 0b0111}
K2_STRINGS = {0b1000, 0b1011, 0b1110, 0b1111}


def build(spec):
    b = Builder(spec)
    a, k2 = spec.alpha, spec.beta

    def angle(s):
        return -0.25 * a if s in K1_STRINGS else -2.0 * k2

    # Bell frame: XX_13 / ZZ_13 and XX_24 / ZZ_24 -> single-qubit Z.
    b.cx(3, 1)
    b.cx(2, 0)
    b.h(3)
    b.h(2)
    rows = [1, 2, 4, 8]
    todo = K1_STRINGS | K2_STRINGS
    for q in range(4):
        if rows[q] in todo:
            b.rz(angle(rows[q]), q)
            todo.discard(rows[q])
    for c, t in NET:
        b.cx(c, t)
        rows[t] ^= rows[c]
        if rows[t] in todo:
            b.rz(angle(rows[t]), t)
            todo.discard(rows[t])
    assert not todo and rows == [1, 2, 4, 8]
    b.h(2)
    b.h(3)
    b.cx(2, 0)
    b.cx(3, 1)
    return b
