"""LSH circuits (prompts/400 section 2; docs/METHODS-lsh.md L7).  `build_UE` (step 7.5), `build_UB` (7.6) and `build_step` (7.7) are built;
`wrap_spinnet` is a STUB (step 7.8) raising NotImplementedError.  Register order: d (12), o (12) if with_outer, then
ancillas."""
from __future__ import annotations

import functools

from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import walk as W

N_DATA, N_OUTER = 12, 12
J_HALF_PHASE = 0.75        # electric energy of a spin-1/2 link: (1/2)(1/2 + 1)


def _pending(name: str, step: str):
    raise NotImplementedError(f"PENDING: su2plaq.circuits.lsh.{name} is not built yet (prompts/400 step {step})")


def build_UE(alpha, with_outer=False, include_outer_electric=False):
    """Electric layer exp(-i alpha H_E) in the LSH register.  N_n = l_pn + l_nv at every 'in' site (never both 1 on valid
    codes) -> p(-3 alpha/4) on qubits 3c and 3c+1 (8 phases, no CX).  include_outer_electric (needs with_outer): at every
    'out' site N_1 + N_2 = 2 l_12 + l_2v + l_v1 -> p(-3 alpha/2) on 12+3c, p(-3 alpha/4) on 12+3c+1 and 12+3c+2 (12 more
    phases)."""
    if include_outer_electric and not with_outer:
        raise ValueError("include_outer_electric needs with_outer=True (the outer qubits must exist)")
    regs = [QuantumRegister(N_DATA, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name="UE")
    for c in range(4):
        qc.p(-J_HALF_PHASE * alpha, 3 * c)
        qc.p(-J_HALF_PHASE * alpha, 3 * c + 1)
    if include_outer_electric:
        for c in range(4):
            qc.p(-2 * J_HALF_PHASE * alpha, N_DATA + 3 * c)
            qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c + 1)
            qc.p(-J_HALF_PHASE * alpha, N_DATA + 3 * c + 2)
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


@functools.lru_cache(maxsize=1)
def _table() -> dict:
    """Coupling table inner code -> K[partner, code] of the LSH operator (the walk angles are solved from it)."""
    return W.coupling_table(LSH())


def _with_meta(qc, steps, **kw):
    theta, _res = W.solve_angles(steps, _table(), kw["beta"])
    qc.metadata = {**kw, "skeleton": "transcode+general7", "angles": [float(t) for t in theta],
                   "angle_fractions": [str(f) for f in W.angle_fractions(steps, _table())]}
    return qc


def build_UB(beta, with_outer=False):
    """U_B(beta) = T^dag [frame H flags walk flags^-1 H frame^-1] T on d[12] + 7 ancillas (docs/METHODS-lsh.md L7); the
    four rotation angles are solved from the LSH coupling table."""
    steps, n_anc = W.skeleton(0)
    return _with_meta(W.build(steps, n_anc, _table(), None, beta, 1, with_outer, "UB"), steps, kind="UB", beta=beta)


def build_step(alpha, beta, order=1, with_outer=False):
    """One Trotter step (order 1: U_B U_E; order 2: U_E/2 U_B U_E/2) with the electric layer applied on the link wires
    inside the transcoded frame (4 phases per layer)."""
    if order not in (1, 2):
        raise ValueError(f"unknown Trotter order {order!r}")
    steps, n_anc = W.skeleton(order)
    return _with_meta(W.build(steps, n_anc, _table(), alpha, beta, order, with_outer, f"step{order}"), steps, kind="step",
                      alpha=alpha, beta=beta, order=order)


def wrap_spinnet(sn_qc, with_outer=False):
    _pending("wrap_spinnet", "7.8")
