"""LSH circuits (prompts/400 section 2; docs/METHODS-lsh.md L7).  `build_UE` is built (step 7.5); `build_UB`, `build_step`,
`wrap_spinnet` are STUBS (steps 7.6-7.8) raising NotImplementedError.  Register order: d (12), o (12) if with_outer, then
ancillas."""
from __future__ import annotations

from qiskit import QuantumCircuit, QuantumRegister

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


def build_UB(beta, with_outer=False):
    _pending("build_UB", "7.6")


def build_step(alpha, beta, order=1, with_outer=False):
    _pending("build_step", "7.7")


def wrap_spinnet(sn_qc, with_outer=False):
    _pending("wrap_spinnet", "7.8")
