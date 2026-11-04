"""Route-A operators and targets (prompts/002 §2.4). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def plaquette_W(link=None, convention: str = "cg") -> np.ndarray:
    todo("plaquette_W")


def h_electric_inner(basis) -> np.ndarray:
    todo("h_electric_inner")


def h_electric_outer(basis) -> np.ndarray:
    todo("h_electric_outer")


def h_magnetic_phys(basis, W: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    todo("h_magnetic_phys")


def hamiltonian_phys(basis, g2: float, include_outer_electric: bool = False) -> np.ndarray:
    todo("hamiltonian_phys")


def target(basis, kind: str, alpha: float | None = None, beta: float | None = None, order: int = 1,
           include_outer_electric: bool = False) -> np.ndarray:
    todo("target")
