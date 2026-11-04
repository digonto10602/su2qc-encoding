"""12-qubit encoding (prompts/002 §2.5). Stubs (step 0.1)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from su2plaq._stub import todo
from su2plaq.encodings.base import ALT_ANGLES, NOMINAL_ANGLES, EncodedBasis, Encoding, Layout  # noqa: F401

if TYPE_CHECKING:
    from qiskit import QuantumCircuit


class TwelveQubit(Encoding):
    name = "twelve"
    n_data = 12
    n_outer = 16
    is_basis_encoding = False
    # bits (q_j q_m q_m') with q_m' = bit 0, q_m = bit 1, q_j = bit 2 at qubits (3l, 3l+1, 3l+2); Paulo basis
    LINK_CODE = {"0": 0b000, "++": 0b111, "+-": 0b110, "-+": 0b101, "--": 0b100}
    # OUTER_CODE (to be built in M0 step 0.8): outer link k at qubits (12+2k, 12+2k+1) = (q_m_near, q_j)

    def __init__(self):
        todo("TwelveQubit")

    def inner_codes(self) -> np.ndarray:
        todo("TwelveQubit.inner_codes")

    def physical_vectors(self) -> EncodedBasis:
        todo("TwelveQubit.physical_vectors")

    def decode(self, code: int) -> int | None:
        todo("TwelveQubit.decode")

    def target(self, kind: str, alpha: float, beta: float, order: int = 1) -> np.ndarray:
        todo("TwelveQubit.target")

    def layout_of(self, qc: "QuantumCircuit") -> Layout:
        todo("TwelveQubit.layout_of")

    def describe(self) -> str:
        todo("TwelveQubit.describe")

    def import_map(self, source: str) -> dict | str:
        todo("TwelveQubit.import_map")
