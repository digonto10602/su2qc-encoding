"""Optional deterministic polish passes (prompts/002 §2.10).

`polish(qc, spec)` applies two exact, structural rewrites to a circuit of BASIS u MACROS gates and keeps the result only if it
is STRICTLY better in the cost key and still valid (trial evaluation); otherwise it returns the input unchanged:

  1. cancel adjacent inverse pairs on the same qubits (x x, h h, z z, s sdg, t tdg, cx cx, cz cz, swap swap, ccx ccx, ccz ccz,
     ch ch, rccx rccx), "adjacent" meaning no other gate acts on any of the pair's qubits in between;
  2. merge adjacent rotations of the same kind on the same qubits (rz, p, crz, crx, cp: angles add).

Both are exact identities and angle-structural (no angle is ever tested for zero), so a skeleton that is angle independent stays
angle independent.
"""
from __future__ import annotations

import numpy as np

_SELF_INVERSE = {"x", "z", "h", "cx", "cz", "swap", "ccx", "ccz", "ch", "rccx"}
_INVERSE = {"s": "sdg", "sdg": "s", "t": "tdg", "tdg": "t"}
_SYMMETRIC = {"cz": True, "swap": True, "ccz": True}      # qubit order does not matter
_MERGE = {"rz", "p", "crz", "crx", "cp"}


def _same_qubits(name, a, b) -> bool:
    return tuple(a) == tuple(b) or (name in _SYMMETRIC and sorted(a) == sorted(b))


def _cancel_and_merge(ops):
    """Fixpoint of the two rewrites on a gate list [(name, params, qubits)]; returns (new list, n_cancelled, n_merged)."""
    n_cancel = n_merge = 0
    changed = True
    while changed:
        changed = False
        out: list = []
        stacks: dict[int, list[int]] = {}       # qubit -> indices into `out` of surviving gates acting on it (in order)
        alive: list[bool] = []
        for name, params, qs in ops:
            tops = {stacks[q][-1] if stacks.get(q) else None for q in qs}
            partner = None
            if len(tops) == 1 and None not in tops:
                j = next(iter(tops))
                if alive[j] and len(out[j][2]) == len(qs) and set(out[j][2]) == set(qs) and all(stacks[q][-1] == j for q in qs):
                    partner = j
            if partner is not None:
                pn, pp, pq = out[partner]
                if (_same_qubits(name, pq, qs) and ((name == pn and name in _SELF_INVERSE) or _INVERSE.get(name) == pn)):
                    alive[partner] = False
                    for q in qs:
                        stacks[q].pop()
                    n_cancel += 2
                    changed = True
                    continue
                if name == pn and name in _MERGE and tuple(pq) == tuple(qs):
                    out[partner] = (pn, (pp[0] + params[0],), pq)
                    n_merge += 1
                    changed = True
                    continue
            out.append((name, params, qs))
            alive.append(True)
            for q in qs:
                stacks.setdefault(q, []).append(len(out) - 1)
        ops = [o for o, a in zip(out, alive) if a]
    return ops, n_cancel, n_merge


def _rebuild(qc, ops):
    from qiskit import QuantumCircuit

    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase, name=qc.name)
    for name, params, qs in ops:
        getattr(out, name)(*params, *[out.qubits[q] for q in qs])
    out.metadata = dict(qc.metadata or {})
    return out


def polish(qc, spec) -> tuple:
    """-> (circuit, log).  The input is returned unchanged (same object) unless the polished circuit is strictly better in key
    (CX, T_eps estimate, depth, qubits) AND valid under the trial evaluation."""
    from su2plaq.compress import builder as B
    from su2plaq.compress.evaluate import _gate_violations, evaluate_circuit
    from su2plaq.compress.metrics import metrics
    from su2plaq.compress.synth import key

    if _gate_violations(qc):
        return qc, ["skipped: the circuit contains gates outside BASIS u MACROS"]
    ops = [(i.operation.name, tuple(float(x) for x in i.operation.params), tuple(qc.find_bit(q).index for q in i.qubits))
           for i in qc.data if i.operation.name != "barrier"]
    new_ops, n_cancel, n_merge = _cancel_and_merge(ops)
    log = [f"cancelled {n_cancel} gates in inverse pairs, merged {n_merge} rotations"]
    if not (n_cancel or n_merge):
        return qc, log + ["nothing to do"]
    cand = _rebuild(qc, new_ops)
    k0, k1 = key(metrics(qc, spec, measured=False)), key(metrics(cand, spec, measured=False))
    if not k1 < k0:
        return qc, log + [f"not strictly better ({k1} vs {k0}); kept the input"]
    r = evaluate_circuit(cand, spec, mode="trial")
    if not r.valid:
        return qc, log + [f"candidate invalid ({r.reason}); kept the input"]
    return cand, log + [f"accepted: key {k0} -> {k1}"]
