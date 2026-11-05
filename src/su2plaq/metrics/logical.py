"""Logical-level metrics (prompts/002 §2.8, docs/METHODS.md §7).

`lower` = level-0 transpile to {cx, h, s, sdg, t, tdg, x, z, rz} with a fixed seed (the design is what is counted, no
optimisation).  CX = number of cx; N_rot = rz at angles that are not multiples of pi/4 (tol 1e-9); T_fixed = t + tdg + rz at
odd multiples of pi/4.
"""
from __future__ import annotations

import math

from su2plaq.evaluate.sparse_sim import _reject_wide_mcx

LOGICAL_BASIS = ["cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz"]
SEED = 20261104


def lower(qc):
    """transpile(qc, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED); raises ValueError on
    'unitary', native mcx with >= 3 controls (also inside custom gates), measure, reset, delay."""
    from qiskit import transpile

    _reject_wide_mcx(qc)
    for inst in qc.data:
        nm = inst.operation.name
        if nm in ("unitary", "measure", "reset", "delay") or nm.startswith("if_") or nm == "for_loop":
            raise ValueError(f"gate {nm!r} cannot be lowered to the logical gate set")
    out = transpile(qc, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED)
    bad = set(out.count_ops()) - set(LOGICAL_BASIS) - {"barrier"}
    if bad:
        raise ValueError(f"lowering left gates outside the logical basis: {sorted(bad)}")
    return out


def is_clifford_t_angle(theta, tol: float = 1e-9) -> bool:
    """True iff theta is a multiple of pi/4."""
    k = float(theta) / (math.pi / 4)
    return abs(k - round(k)) < tol


def logical_metrics(qc) -> dict:
    """{"cx","depth","n_rot","t_fixed","qubits","ancilla","gates","rz_angles"} of the level-0 lowering of `qc`.
    qubits = qc.num_qubits; ancilla = qubits - size of register "d" - size of register "o" (if present)."""
    low = lower(qc)
    ops = low.count_ops()
    n_rot, t_fixed, angles = 0, ops.get("t", 0) + ops.get("tdg", 0), []
    for inst in low.data:
        if inst.operation.name == "rz":
            th = float(inst.operation.params[0])
            if is_clifford_t_angle(th):
                if round(th / (math.pi / 4)) % 2 != 0:
                    t_fixed += 1
            else:
                n_rot += 1
                angles.append(th)
    sizes = {reg.name: len(reg) for reg in qc.qregs}
    return {"cx": ops.get("cx", 0), "depth": low.depth(), "n_rot": n_rot, "t_fixed": t_fixed, "qubits": qc.num_qubits,
            "ancilla": qc.num_qubits - sizes.get("d", 0) - sizes.get("o", 0), "gates": dict(ops), "rz_angles": angles}
