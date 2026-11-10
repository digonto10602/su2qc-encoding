"""Seed circuits and programs of round 0 (prompts/203 section 3.1, research 202 section 2.4).

The laptop `compress.baselines` hard-codes the twelve circuit in `general_circuit`, `qiskit_l3(_whole)` and `general_polished`
(and `passes.polish` calls the laptop evaluator), so this module has rishon copies of exactly those: the general circuit in three
control-ladder styles, the windowed Qiskit level-3 baseline of OUR general circuit, the polish passes driven by OUR trial
evaluation, and `import_seed`, which for rishon is always a reason (no external circuit acts on rishon codes).  The pure helpers of
the laptop (`program_source`, `_gate_list`, `_cancel_and_merge`, `_rebuild`, `L3_WINDOW`) are reused unchanged.
"""
from __future__ import annotations

import pathlib

import numpy as np

from su2plaq.compress.spec import get_encoding

LADDERS = ("ccx", "rccx", "mcx")


def general_circuit(spec, ladder: str = "ccx"):
    """circuits.rishon.build_UE/UB/step(..., with_outer=True, ladder=ladder): the reference circuit for the spec's kind, order and
    angles (registers d, o, then the ancilla register).  `ladder` only matters for kinds with U_B."""
    from su2plaq.circuits import rishon as C

    if ladder not in LADDERS:
        raise ValueError(f"ladder must be one of {LADDERS}, got {ladder!r}")
    if spec.kind == "UE":
        return C.build_UE(spec.alpha, with_outer=True)
    if spec.kind == "UB":
        return C.build_UB(spec.beta, with_outer=True, ladder=ladder)
    return C.build_step(spec.alpha, spec.beta, spec.order, with_outer=True, ladder=ladder)


_LADDER_NUMBER = {"ccx": "000", "rccx": "001", "mcx": "002"}


def general_program_path(spec, ladder: str = "ccx") -> pathlib.Path:
    """compress/programs/rishon/seed/000-general[-<kind>].py (ccx), 001-general-rccx[-<kind>].py, 002-general-mcx[-<kind>].py,
    generated on first use by the laptop `program_source` (angle-linear; afterwards the file is immutable)."""
    from su2plaq.compress import baselines as LB
    from su2plaq.compress.spec import ROOT

    if ladder not in LADDERS:
        raise ValueError(f"ladder must be one of {LADDERS}, got {ladder!r}")
    base = "general" if ladder == "ccx" else f"general-{ladder}"
    path = ROOT / "compress" / "programs" / spec.encoding / LB.SEED_FAMILY / f"{_LADDER_NUMBER[ladder]}-{LB._stem(spec, base)}.py"
    if not path.exists():
        style = "" if ladder == "ccx" else f" with {ladder} control ladders"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LB.program_source(lambda s: general_circuit(s, ladder), spec, summary=f"the reference circuit of the "
                        f"{spec.encoding} encoding ({spec.kind}){style} expressed through the Builder; every angle is a linear "
                        "function of spec.alpha / spec.beta."))
    return path


def linear_in_angles(circuit_fn, spec):
    """`circuit_fn` with every angle replaced by its exact linear form c_a alpha + c_b beta, fitted at generic angle pairs (the
    nominal and alternate pairs and two more) and checked to 1e-10.  The laptop `program_source` fits at (0,0), (1,0), (0,1), where
    an optimising transpile (the Qiskit level-3 baseline) drops zero-angle rotations and changes the skeleton; at generic pairs the
    skeleton is stable.  Raises ValueError if the skeleton differs between the pairs or an angle is not linear homogeneous."""
    from qiskit import QuantumCircuit

    from su2plaq.compress import baselines as LB

    points = [(spec.alpha, spec.beta), *spec.alt_angles, (0.50, 0.50), (0.20, 1.30)]
    gls = [LB._gate_list(circuit_fn(spec.with_angles(a, b))) for a, b in points]
    skel = [[(n, q) for n, _p, q in g] for g in gls]
    if any(k != skel[0] for k in skel):
        raise ValueError("the circuit skeleton depends on the angles at the generic fit points; no angle-linear program exists")
    A = np.array(points)
    coeffs = {}
    for k, (name, params, _q) in enumerate(gls[0]):
        if params:
            y = np.array([g[k][1][0] for g in gls])
            c = np.linalg.lstsq(A, y, rcond=None)[0]
            if np.abs(A @ c - y).max() > 1e-10:
                raise ValueError(f"angle of gate {k} ({name}) is not linear homogeneous in (alpha, beta)")
            coeffs[k] = (float(c[0]), float(c[1]))
    base = circuit_fn(spec)

    def fn(s):
        out = QuantumCircuit(*base.qregs, global_phase=base.global_phase)
        for k, inst in enumerate(base.data):
            op = inst.operation
            if k in coeffs:
                op = type(op)(coeffs[k][0] * s.alpha + coeffs[k][1] * s.beta)
            out.append(op, [base.find_bit(q).index for q in inst.qubits])
        return out
    return fn


def qiskit_l3_whole(spec, seed: int = 12345):
    """Whole-circuit level-3 transpile of the general circuit into the Builder basis (idle qubits not assumed clean).  Qiskit hoists
    Hadamards across the whole circuit (far more than 1e6 amplitudes per input), so this version cannot be verified by the exact
    sparse engine: counts only."""
    from qiskit import transpile

    from su2plaq.compress import builder as B

    return transpile(general_circuit(spec), basis_gates=sorted(B.BASIS), optimization_level=3, seed_transpiler=seed,
                     qubits_initially_zero=False)


def qiskit_l3(spec, seed: int = 12345, window: int | None = None):
    """The Qiskit level-3 baseline: the general circuit is cut into windows of `window` consecutive instructions (default the laptop's
    `L3_WINDOW` = 32), each window is transpiled with optimization_level=3 (seed `seed`, Builder basis, idle qubits not assumed
    clean) and the results are concatenated in program order; the same definition as the laptop's, applied to the rishon circuit."""
    from qiskit import QuantumCircuit, transpile

    from su2plaq.compress import baselines as LB
    from su2plaq.compress import builder as B

    window = LB.L3_WINDOW if window is None else window
    qc = general_circuit(spec)
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase, name="qiskit_l3")
    data = list(qc.data)
    for s0 in range(0, len(data), window):
        chunk = data[s0:s0 + window]
        qs = sorted({qc.find_bit(q).index for i in chunk for q in i.qubits})
        idx = {q: k for k, q in enumerate(qs)}
        sub = QuantumCircuit(len(qs))
        for i in chunk:
            sub.append(i.operation, [idx[qc.find_bit(q).index] for q in i.qubits])
        t = transpile(sub, basis_gates=sorted(B.BASIS), optimization_level=3, seed_transpiler=seed, qubits_initially_zero=False)
        out.compose(t, qubits=[out.qubits[q] for q in qs], inplace=True)      # compose adds t.global_phase
    return out


def polish(qc, spec):
    """-> (circuit, log).  The laptop's two exact structural rewrites (cancel adjacent inverse pairs, merge adjacent rotations: the
    rules `cancel_inverse_pairs` / `merge_adjacent_rotations` of `su2plaq.lean.rules.LEAN_RULES`), kept only if the cost key is
    STRICTLY better and OUR trial evaluation (rishon inner-block verdict) accepts the result; otherwise the input object is returned.
    Every log line starts with the rule name."""
    from su2plaq.compress import passes as LP
    from su2plaq.compress.evaluate import _gate_violations
    from su2plaq.compress.metrics import metrics
    from su2plaq.compress.synth import key
    from su2plaq.rishon.compress.evaluate import evaluate_circuit

    if _gate_violations(qc):
        return qc, ["cancel_inverse_pairs: skipped, the circuit contains gates outside BASIS u MACROS"]
    ops = [(i.operation.name, tuple(float(x) for x in i.operation.params), tuple(qc.find_bit(q).index for q in i.qubits))
           for i in qc.data if i.operation.name != "barrier"]
    new_ops, n_cancel, n_merge = LP._cancel_and_merge(ops)
    log = [f"cancel_inverse_pairs: {n_cancel} gates removed in inverse pairs", f"merge_adjacent_rotations: {n_merge} rotations merged"]
    if not (n_cancel or n_merge):
        return qc, log + ["cancel_inverse_pairs: nothing to do"]
    cand = LP._rebuild(qc, new_ops)
    k0, k1 = key(metrics(qc, spec, measured=False)), key(metrics(cand, spec, measured=False))
    if not k1 < k0:
        return qc, log + [f"cancel_inverse_pairs: not strictly better ({k1} vs {k0}); kept the input"]
    r = evaluate_circuit(cand, spec, mode="trial")
    if not r.valid:
        return qc, log + [f"cancel_inverse_pairs: candidate invalid ({r.reason}); kept the input"]
    return cand, log + [f"cancel_inverse_pairs: accepted, key {k0} -> {k1}"]


def general_polished(spec):
    return polish(general_circuit(spec), spec)


def import_seed(spec, source: str) -> str:
    """Always a reason string: no external circuit (paulo34, lean22, lean22_v2, spinnet15) acts on rishon codes.  Unknown source:
    ValueError."""
    return get_encoding(spec.encoding).import_map(source)
