"""SU(2) link algebra, Paulo's basis (prompts/002 §2.2). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo

# Pauli matrices (fixed data, not physics to be derived).
SIGMA: list[np.ndarray] = [
    np.array([[0, 1], [1, 0]], dtype=np.complex128),
    np.array([[0, -1j], [1j, 0]], dtype=np.complex128),
    np.array([[1, 0], [0, -1]], dtype=np.complex128),
]
PAULO_ORDER = ("0", "++", "+-", "-+", "--")


def spin_matrices(j) -> list[np.ndarray]:
    todo("spin_matrices")


def m_values(j) -> list[float]:
    todo("m_values")


def clebsch_gordan(j1, m1, j2, m2, J, M) -> float:
    todo("clebsch_gordan")


class LinkSpace:
    """Copy of su2qc-skqd src/skqd/su2.py (source commit to be cited when implemented)."""

    spins: list
    states: list
    index: dict
    dim: int

    def __init__(self, jmax: float = 0.5):
        todo("LinkSpace")

    def U(self) -> list[list[np.ndarray]]:
        todo("LinkSpace.U")

    def generators(self) -> tuple[list[np.ndarray], list[np.ndarray]]:
        todo("LinkSpace.generators")

    def casimir(self) -> np.ndarray:
        todo("LinkSpace.casimir")


def paulo_U() -> list[list[np.ndarray]]:
    todo("paulo_U")


def paulo_adapter() -> np.ndarray:
    todo("paulo_adapter")
