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


_LOWER_CACHE: dict = {}


def _lower_gate(op):
    """Level-0 decomposition of one gate on qubits 0..k-1 into LOGICAL_BASIS: ([(name, local qubits, params)], phase);
    cached for standard-library gates only (never on a name alone)."""
    from qiskit import QuantumCircuit, transpile

    from su2plaq.evaluate.sparse_sim import decomposition_cache_key

    key = decomposition_cache_key(op)
    if key is not None and key in _LOWER_CACHE:
        return _LOWER_CACHE[key]
    sub = QuantumCircuit(op.num_qubits)
    sub.append(op, list(range(op.num_qubits)), [])
    t = transpile(sub, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED, qubits_initially_zero=False)
    res = ([(i.operation.name, tuple(t.find_bit(q).index for q in i.qubits), tuple(i.operation.params)) for i in t.data
            if i.operation.name != "barrier"], float(t.global_phase))
    if key is not None:
        _LOWER_CACHE[key] = res
    return res


def lower(qc):
    """Level-0 lowering to {cx, h, s, sdg, t, tdg, x, z, rz}, gate by gate in PROGRAM ORDER (each foreign gate is replaced in
    place by its own transpile(basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED,
    qubits_initially_zero=False); a whole-circuit transpile would reorder the DAG layer by layer and hoist every Hadamard of
    the Toffoli expansions together, which makes the lowered circuit impractical to simulate).  Same counts as the
    whole-circuit lowering.  Raises ValueError on 'unitary', native mcx with >= 3 controls (also inside custom gates),
    measure, reset, delay, classical control."""
    from qiskit import QuantumCircuit

    _reject_wide_mcx(qc)
    for inst in qc.data:
        nm = inst.operation.name
        if nm in ("unitary", "measure", "reset", "delay") or nm.startswith("if_") or nm in ("for_loop", "while_loop", "switch_case") or inst.clbits:
            raise ValueError(f"gate {nm!r} cannot be lowered to the logical gate set")
    from qiskit.circuit.library.standard_gates import get_standard_gate_name_mapping

    from su2plaq.evaluate.sparse_sim import decomposition_cache_key

    std = get_standard_gate_name_mapping()
    out = QuantumCircuit(*qc.qregs, *qc.cregs, global_phase=qc.global_phase, name=qc.name)
    phase = [0.0]

    def emit(op, qs, depth=0):
        if op.name == "barrier":
            return
        if op.name in LOGICAL_BASIS:
            out.append(op, qs, [])
        elif decomposition_cache_key(op) is not None or getattr(op, "definition", None) is None or depth > 30:
            local, ph = _lower_gate(op)
            phase[0] += ph
            for nm, lq, params in local:
                out.append(std[nm].__class__(*params) if params else std[nm].copy(), [qs[k] for k in lq], [])
        else:   # custom / composite gate: inline its definition in program order
            d = op.definition
            phase[0] += float(d.global_phase)
            for inst in d.data:
                emit(inst.operation, [qs[d.find_bit(q).index] for q in inst.qubits], depth + 1)

    for inst in qc.data:
        emit(inst.operation, [out.qubits[qc.find_bit(q).index] for q in inst.qubits])
    out.global_phase = float(qc.global_phase) + phase[0]
    bad = set(out.count_ops()) - set(LOGICAL_BASIS)
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
