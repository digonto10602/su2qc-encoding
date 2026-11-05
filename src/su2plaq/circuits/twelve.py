"""12-qubit circuits (prompts/002 §2.6; docs/METHODS.md §2). Register order: d (12), then o (16) if present, then ancillas."""
from __future__ import annotations

from su2plaq._stub import todo

N_DATA, N_OUTER = 12, 16
INNER_J_QUBITS = (2, 5, 8, 11)          # q_j of the inner links b, r, t, l (qubits 3l + 2)
OUTER_J_QUBITS = tuple(12 + 2 * k + 1 for k in range(8))   # q_j of outer link k (qubits 12 + 2k + 1)


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    """Electric step U_E(alpha) = exp(-i alpha H_E^inner): one p(-3 alpha / 4) on the j-qubit of each inner link (the code
    of a j = 1/2 link has q_j = 1 and j(j+1) = 3/4; Qiskit p(l) = diag(1, e^{il})).  Registers d[12] (+ o[16] if
    `with_outer`); metadata {"kind": "UE", "alpha": alpha}.

    include_outer_electric (needs with_outer) adds the same p(-3 alpha / 4) on the j-qubit of each of the 8 outer links,
    i.e. exp(-i alpha (H_E^inner + H_E^outer)) = operators.target(..., "UE", include_outer_electric=True)."""
    from qiskit import QuantumCircuit, QuantumRegister

    if include_outer_electric and not with_outer:
        raise ValueError("include_outer_electric needs with_outer=True")
    regs = [QuantumRegister(N_DATA, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name="UE")
    lam = -0.75 * alpha
    for q in INNER_J_QUBITS:
        qc.p(lam, q)
    if include_outer_electric:
        for q in OUTER_J_QUBITS:
            qc.p(lam, q)
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


def build_UB(beta: float, with_outer: bool = False):
    todo("build_UB")


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False):
    todo("build_step")


def paulo_logical(beta: float = 1.0):
    todo("paulo_logical")


def paulo_circuit():
    todo("paulo_circuit")
