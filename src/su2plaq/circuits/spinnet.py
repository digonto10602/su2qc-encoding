"""16-qubit spin-network circuits (prompts/100 §2; docs/METHODS-spinnet.md §4).  Register order: d (8), then o (8) if
with_outer, then ancillas.  build_UE / build_UB / build_step (steps 3.3-3.5); paulo_circuit (3.2); trotter_v2 stub (3.6)."""
from __future__ import annotations

import functools

from qiskit import QuantumCircuit, QuantumRegister

from su2plaq._stub import todo
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet import paulo
from su2plaq.spinnet.walk import FRAME, GENERAL7, TARGET, angle_fractions, build_walk, coupling_table, solve_angles

N_DATA, N_OUTER = 8, 8
LINK_QUBITS = (0, 1, 2, 3)
CORNER_QUBITS = (4, 5, 6, 7)
OUTER_QUBITS = tuple(range(8, 16))
J_HALF_PHASE = 3.0 / 4.0          # j(j+1) at j = 1/2: an excited link qubit carries H_E = 3/4


@functools.lru_cache(maxsize=1)
def _table() -> dict:
    """Coupling table of K (inner code -> K entry), computed once from the encoding."""
    return coupling_table(SpinNet())


def _electric_layer(qc: QuantumCircuit, alpha: float, outer_qubits=()) -> None:
    for q in tuple(LINK_QUBITS) + tuple(outer_qubits):
        qc.p(-J_HALF_PHASE * alpha, q)


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    """p(-3 alpha / 4) on the four inner-link qubits (+ the 8 outer ones with include_outer_electric)."""
    if include_outer_electric and not with_outer:
        raise ValueError("include_outer_electric needs with_outer=True (the outer qubits must exist)")
    regs = [QuantumRegister(N_DATA, "d")] + ([QuantumRegister(N_OUTER, "o")] if with_outer else [])
    qc = QuantumCircuit(*regs, name="UE")
    _electric_layer(qc, alpha, OUTER_QUBITS if include_outer_electric else ())
    qc.metadata = {"kind": "UE", "alpha": alpha}
    return qc


def build_UB(beta: float, with_outer: bool = False):
    """Frame + flags + 4-rotation phase walk (GENERAL7), angles solved from K at every call."""
    steps, n_anc = GENERAL7
    qc = build_walk(steps, _table(), beta, n_anc, with_outer=with_outer, name="UB")
    theta, _ = solve_angles(steps, _table(), beta)
    qc.metadata = {"kind": "UB", "beta": beta, "skeleton": "general7", "angles": [float(t) for t in theta],
                   "angle_fractions": [str(f) for f in angle_fractions(steps, _table())]}
    return qc


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False):
    """U_E then U_B (order 1) / U_E(alpha/2) U_B U_E(alpha/2) (order 2); the outer electric phases are not included."""
    if order not in (1, 2):
        raise ValueError(f"unknown Trotter order {order!r}")
    ub = build_UB(beta, with_outer)
    qc = QuantumCircuit(*ub.qregs, name=f"step{order}")
    half = alpha if order == 1 else alpha / 2
    _electric_layer(qc, half)
    qc.compose(ub, inplace=True)
    if order == 2:
        _electric_layer(qc, half)
    qc.metadata = {"kind": "step", "alpha": alpha, "beta": beta, "order": order, "skeleton": "general7"}
    return qc


def paulo_circuit(with_outer: bool = False):
    """refs/paulo/spin_network_plaquette3.gates.txt as a QuantumCircuit (gates as in the file, global phase 0), registers
    d[8] (+ o[8]) a[7]; metadata kind UB, alpha_P = 0.1, beta = alpha_P / 2 (Paulo Eq. 16 normalisation), source, sha256."""
    qc = paulo.load_circuit(with_outer)
    qc.metadata = {"kind": "UB", "alpha_P": paulo.FILE_ALPHA_P, "beta": paulo.FILE_ALPHA_P / 2,
                   "source": str(paulo.GATES_FILE), "sha256": paulo.SHA256}
    return qc


def trotter_v2_circuit(skeleton: str, beta: float, with_outer: bool = False):
    """Vendored spinnet_v2 skeleton ("pairs9", "flags4", "flags5", "flags6") with angles solved from K."""
    return todo("circuits.spinnet.trotter_v2_circuit")
