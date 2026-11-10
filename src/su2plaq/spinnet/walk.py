"""Skeleton language and exact angle solve for the spin-network phase-walk circuits (prompts/100 §1.5, §2).

`coupling_table` (3.1); `classical_slots`, `solve_angles`, `angle_fractions`, `mirror`, `build_walk` (3.2).  Skeleton
data (GENERAL7 here; the trotter_v2 skeletons in step 3.6) are lists of Steps on wires data 0..7, ancillas 8..;
the angle of every `rz` is solved from K, never typed in."""
from __future__ import annotations

from fractions import Fraction

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import RC3XGate

# Step = ("cx", c, t) | ("x", q) | ("rccx", a, b, t) | ("rc3x", a, b, c, t) | ("rc3x_dg", a, b, c, t) | ("rz", q)
# wires: data 0..7, ancillas 8.. (relabelled after the outer register when with_outer)
Step = tuple
FRAME = ((1, 3), (0, 1), (0, 2))
TARGET = 0
FLIP = 0b1111


def coupling_table(enc) -> dict[int, float]:
    """inner code -> K[partner, code] (0.0 for dark codes), snapped to the nearest half-integer (ValueError if K is not
    within 1e-12 of one); partner = code ^ 0b1111 (all four inner spins flip, corner bits unchanged).  Raises if K has
    any other non-zero entry in the column (K must be a matching on the inner codes)."""
    codes = enc.inner_codes()
    pos = {int(c): i for i, c in enumerate(codes)}
    K = enc.K_codes
    table: dict[int, float] = {}
    for c, i in pos.items():
        nz = np.flatnonzero(np.abs(K[:, i]) > 1e-12)
        if len(nz) == 0:
            table[c] = 0.0
            continue
        partner = c ^ FLIP
        if len(nz) != 1 or partner not in pos or nz[0] != pos[partner]:
            raise ValueError(f"K is not a pair matching at inner code {c:08b}")
        v = float(K[nz[0], i])
        if abs(2.0 * v - round(2.0 * v)) > 1e-12:
            raise ValueError(f"K at inner code {c:08b} is {v!r}, not a half-integer within 1e-12")
        table[c] = round(2.0 * v) / 2.0
    return table


def classical_slots(steps, code: int, frame=FRAME) -> list[int]:
    """Bit of the rz wire at every rz for input `code` taken through the frame with the target bit cleared (Toffoli
    semantics for rccx / rc3x / rc3x_dg; ancillas start at 0)."""
    x = int(code)
    for a, b in frame:
        if (x >> a) & 1:
            x ^= 1 << b
    x &= ~(1 << TARGET)
    slots = []
    for st in steps:
        op = st[0]
        if op == "cx":
            if (x >> st[1]) & 1:
                x ^= 1 << st[2]
        elif op == "x":
            x ^= 1 << st[1]
        elif op in ("rccx", "rc3x", "rc3x_dg"):
            if all((x >> q) & 1 for q in st[1:-1]):
                x ^= 1 << st[-1]
        elif op == "rz":
            slots.append((x >> st[1]) & 1)
        else:
            raise ValueError(f"unknown step {st!r}")
    return slots


def _system(steps, table, frame):
    codes = sorted(table)
    A = np.array([[(-1.0) ** v for v in classical_slots(steps, c, frame)] for c in codes])
    k = np.array([table[c] for c in codes])
    return A, k


def solve_angles(steps, table, beta: float, frame=FRAME):
    """theta_r with sum_r theta_r (-1)^{p_r(y)} = 2 beta k(y) on every valid slot; returns (angles, max residual)."""
    A, k = _system(steps, table, frame)
    b = 2.0 * beta * k
    theta, *_ = np.linalg.lstsq(A, b, rcond=None)
    return theta, float(np.abs(A @ theta - b).max())


def angle_fractions(steps, table, frame=FRAME, max_den: int = 64) -> list[Fraction]:
    """theta_r / beta as exact fractions (residual of the rational solution <= 1e-12 asserted)."""
    theta, _ = solve_angles(steps, table, 1.0, frame)
    fr = [Fraction(float(t)).limit_denominator(max_den) for t in theta]
    A, k = _system(steps, table, frame)
    res = float(np.abs(A @ np.array([float(f) for f in fr]) - 2.0 * k).max())
    if res > 1e-12:
        raise ValueError(f"angles are not rational with denominator <= {max_den} (residual {res:.2e})")
    return fr


def mirror(steps) -> list:
    """Uncompute: reversed, rz dropped, rc3x <-> rc3x_dg (rccx is Hermitian, hence self-inverse; Qiskit's RC3XGate is not)."""
    inv = {"rc3x": "rc3x_dg", "rc3x_dg": "rc3x"}
    return [(inv.get(s[0], s[0]),) + tuple(s[1:]) for s in reversed(steps) if s[0] != "rz"]


def build_walk(steps, table, beta: float, n_anc: int, frame=FRAME, with_outer: bool = False, name: str = "UB",
               expand: bool = False):
    """frame; h(TARGET); steps; h(TARGET); frame^-1 as a QuantumCircuit (registers d, [o], a); every rz angle is solved
    from `table` (ValueError if the skeleton cannot reproduce it, residual > 1e-9).  expand=True writes rc3x / rc3x_dg as
    the h / t / tdg / cx definitions of RC3XGate() / RC3XGate().inverse() instead of the composite gates."""
    theta, res = solve_angles(steps, table, beta, frame)
    if res > 1e-9:
        raise ValueError(f"skeleton does not reproduce the coupling table: residual {res:.2e}")
    angles = iter(theta)
    regs = [QuantumRegister(8, "d")] + ([QuantumRegister(8, "o")] if with_outer else []) + [QuantumRegister(n_anc, "a")]
    qc = QuantumCircuit(*regs, name=name)
    off = 16 if with_outer else 8

    def Q(i):
        return i if i < 8 else off + (i - 8)

    for a, b in frame:
        qc.cx(Q(a), Q(b))
    qc.h(Q(TARGET))
    for st in steps:
        op = st[0]
        if op == "cx":
            qc.cx(Q(st[1]), Q(st[2]))
        elif op == "x":
            qc.x(Q(st[1]))
        elif op == "rccx":
            qc.rccx(*[Q(i) for i in st[1:]])
        elif op in ("rc3x", "rc3x_dg"):
            gate = RC3XGate() if op == "rc3x" else RC3XGate().inverse()
            qubits = [Q(i) for i in st[1:]]
            if expand:
                qc.compose(gate.definition, qubits=qubits, inplace=True)
            else:
                qc.append(gate, qubits)
        elif op == "rz":
            qc.rz(float(next(angles)), Q(st[1]))
        else:
            raise ValueError(f"unknown step {st!r}")
    qc.h(Q(TARGET))
    for a, b in reversed(frame):
        qc.cx(Q(a), Q(b))
    return qc


_CORNERS = (4, 5, 6, 7)
_A, _B, _F, _P, _Q, _G1, _G2 = range(8, 15)


def _general7():
    """A = ~c0 ~c1, B = ~c2 ~c3, F = A B (bright flag), P = ~m2 ~m3, Q = F P, G1 = Q ~m1 (vacuum pair), G2 = Q m1
    (alternating pair); four rotations on the frame target (METHODS-spinnet §4)."""
    compute = [("x", q) for q in _CORNERS] + [("rccx", 4, 5, _A), ("rccx", 6, 7, _B), ("rccx", _A, _B, _F),
                                              ("x", 2), ("x", 3), ("rccx", 2, 3, _P), ("rccx", _F, _P, _Q),
                                              ("x", 1), ("rccx", _Q, 1, _G1), ("x", 1), ("rccx", _Q, 1, _G2)]
    walk = [("rz", TARGET)]
    for w in (_F, _G1, _G2):
        walk += [("cx", w, TARGET), ("rz", TARGET), ("cx", w, TARGET)]
    return compute + walk + mirror(compute), 7


GENERAL7: tuple = _general7()
