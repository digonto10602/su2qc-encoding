"""48-qubit rishon circuits (prompts/200 §2.5; METHODS-rishon R7). `build_UE` (5.6); the rest in 5.7-5.8."""
from __future__ import annotations

from su2plaq._stub import todo

N_DATA, N_OUTER = 16, 32


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    """Electric step U_E(alpha) = exp(-i alpha H_E^inner) on the 1296 inner codes (METHODS-rishon R7).

    On a valid link code the link is a quartet (j = 1/2, H_E = 3/4) iff n_{L1} xor n_{L2} = 1 (A = 1100 and B = 0011 have
    equal L bits, the four Q codes differ).  Per link: CX(L1 -> L2), p(-3 alpha / 4) on L2, CX(L1 -> L2) multiplies a
    quartet by e^{-3 i alpha / 4} and leaves A, B alone (2 CX + 1 rotation).  Registers d[16] (+ o[32] if `with_outer`);
    metadata {"kind": "UE", "alpha": alpha}.

    include_outer_electric (needs with_outer) adds the same three gates on each of the 8 outer links: the quartet test is
    valid there too (near end free, far end fixed by the type), giving exp(-i alpha (H_E^inner + H_E^outer)); the outer
    qubits are used only as CX controls/targets that are restored, so every outer basis state is returned unchanged."""
    from qiskit import QuantumCircuit, QuantumRegister

    if include_outer_electric and not with_outer:
        raise ValueError("include_outer_electric needs with_outer=True")
    regs = [QuantumRegister(N_DATA, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name="UE")
    n_links = 4 + (8 if include_outer_electric else 0)
    lam = -0.75 * alpha
    for link in range(n_links):
        l1, l2 = 4 * link, 4 * link + 1
        qc.cx(l1, l2)
        qc.p(lam, l2)
        qc.cx(l1, l2)
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


def build_UB(beta: float, with_outer: bool = False):
    todo("circuits.rishon.build_UB")


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False):
    todo("circuits.rishon.build_step")


def pair_frames(beta: float) -> list[dict]:
    todo("circuits.rishon.pair_frames")
