"""Skeleton language and exact angle solve for the spin-network phase-walk circuits (prompts/100 §1.5, §2).

Step 3.1 builds `coupling_table`; the rest are stubs (steps 3.2 / 3.4)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo

# Step = ("cx", c, t) | ("x", q) | ("rccx", a, b, t) | ("rc3x", a, b, c, t) | ("rc3x_dg", a, b, c, t) | ("rz", q)
# wires: data 0..7, ancillas 8.. (relabelled after the outer register when with_outer)
Step = tuple
FRAME = ((1, 3), (0, 1), (0, 2))
TARGET = 0
FLIP = 0b1111


def coupling_table(enc) -> dict[int, float]:
    """inner code -> K[partner, code] (0.0 for dark codes); partner = code ^ 0b1111 (all four inner spins flip, corner
    bits unchanged).  Raises if K has any other non-zero entry in the column (K must be a matching on the inner codes)."""
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
        table[c] = float(K[nz[0], i])
    return table


def classical_slots(steps, code: int, frame=FRAME) -> list[int]:
    """Bit of the rz wire at every rz for input `code` taken through the frame with the target bit cleared."""
    return todo("walk.classical_slots")


def solve_angles(steps, table, beta: float, frame=FRAME):
    """theta_r with sum_r theta_r (-1)^{p_r(y)} = 2 beta k(y) on every valid slot; returns (angles, max residual)."""
    return todo("walk.solve_angles")


def angle_fractions(steps, table, frame=FRAME, max_den: int = 64):
    """theta_r / beta as exact fractions (|residual| <= 1e-12 asserted)."""
    return todo("walk.angle_fractions")


def mirror(steps) -> list:
    """Uncompute: reversed, rz dropped, rc3x <-> rc3x_dg (rccx is self-inverse)."""
    return todo("walk.mirror")


def build_walk(steps, table, beta: float, n_anc: int, frame=FRAME, with_outer: bool = False, name: str = "UB"):
    """frame; h(TARGET); steps; h(TARGET); frame^-1 as a QuantumCircuit (registers d, [o], a)."""
    return todo("walk.build_walk")
