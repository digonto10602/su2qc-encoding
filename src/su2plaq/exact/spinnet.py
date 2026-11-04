"""Route-B (spin network) cross-check (prompts/002 §2.4). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def labels(diagram=None, jmax: float = 0.5) -> list[tuple]:
    todo("spinnet.labels")


def inner_labels(jmax: float = 0.5) -> list[tuple]:
    todo("inner_labels")


def plaquette_P(labels) -> np.ndarray:
    todo("plaquette_P")


def K_inner(jmax: float = 0.5) -> np.ndarray:
    todo("K_inner")


def h_magnetic_phys_6j(labels) -> np.ndarray:
    todo("h_magnetic_phys_6j")


def h_electric_6j(labels, inner_only: bool = True) -> np.ndarray:
    todo("h_electric_6j")
