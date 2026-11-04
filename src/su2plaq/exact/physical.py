"""Route-A physical basis (prompts/002 §2.3). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from su2plaq._stub import todo
from su2plaq.geometry import Diagram


def corner_singlets(js: tuple[float, float, float, float], roles: tuple[str, str, str, str]) -> tuple[np.ndarray, tuple[float, ...]]:
    todo("corner_singlets")


@dataclass
class PhysicalBasis:
    diagram: Diagram
    jmax: float
    convention: str  # 'cg' | 'paulo'
    labels: list[tuple[tuple[float, ...], tuple[float, ...]]]
    keys: list[np.ndarray]
    amps: list[np.ndarray]
    dim: int

    def index(self, label) -> int:
        todo("PhysicalBasis.index")

    @staticmethod
    def inner_key(keys) -> np.ndarray:
        return np.asarray(keys) % 625

    @staticmethod
    def outer_key(keys) -> np.ndarray:
        return np.asarray(keys) // 625


def physical_basis(diagram: Diagram | None = None, jmax: float = 0.5, convention: str = "cg") -> PhysicalBasis:
    todo("physical_basis")


def apply_link_op(keys, amps, link: int, M: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    todo("apply_link_op")


def gauss_residual(basis: PhysicalBasis, keys, amps) -> float:
    todo("gauss_residual")


def gauss_residuals(basis) -> np.ndarray:
    todo("gauss_residuals")


def gram(basis) -> np.ndarray:
    todo("gram")


def counts(basis) -> dict:
    todo("counts")


def s_o_support(basis) -> dict[int, np.ndarray]:
    todo("s_o_support")


def s_o_dims(basis) -> dict[int, int]:
    todo("s_o_dims")


def inner_span(basis) -> np.ndarray:
    todo("inner_span")


def to_convention(basis, convention: str) -> PhysicalBasis:
    todo("to_convention")
