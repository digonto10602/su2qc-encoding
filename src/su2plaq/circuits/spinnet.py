"""16-qubit spin-network circuits (prompts/100 §2; docs/METHODS-spinnet.md §4).  Register order: d (8), then o (8) if
with_outer, then ancillas.  Stubs (steps 3.2-3.6)."""
from __future__ import annotations

from su2plaq._stub import todo
from su2plaq.spinnet import paulo

N_DATA, N_OUTER = 8, 8
LINK_QUBITS = (0, 1, 2, 3)
CORNER_QUBITS = (4, 5, 6, 7)
OUTER_QUBITS = tuple(range(8, 16))
FRAME = ((1, 3), (0, 1), (0, 2))
TARGET = 0


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    """p(-3 alpha / 4) on the four inner-link qubits (+ the 8 outer ones with include_outer_electric)."""
    return todo("circuits.spinnet.build_UE")


def build_UB(beta: float, with_outer: bool = False):
    """Frame + flags + 4-rotation phase walk (GENERAL7), angles solved from K."""
    return todo("circuits.spinnet.build_UB")


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False):
    """U_E then U_B (order 1) / U_E(alpha/2) U_B U_E(alpha/2) (order 2)."""
    return todo("circuits.spinnet.build_step")


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
