"""Rishon inner operators on the 1296 valid 16-bit codes (prompts/200 §2.3; METHODS-rishon R4).
Stubs (step 5.0); built in step 5.3."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def inner_codes() -> np.ndarray:
    todo("rishon.operators.inner_codes")


def plaquette_W_inner() -> np.ndarray:
    todo("rishon.operators.plaquette_W_inner")


def h_electric_inner() -> np.ndarray:
    todo("rishon.operators.h_electric_inner")


def h_magnetic_inner() -> np.ndarray:
    todo("rishon.operators.h_magnetic_inner")


def gauss_inner(corner: int, a: int) -> np.ndarray:
    todo("rishon.operators.gauss_inner")


def heights(code: int) -> tuple[int, int, int, int]:
    todo("rishon.operators.heights")


def bright_pairs() -> list[tuple[np.ndarray, np.ndarray, float]]:
    todo("rishon.operators.bright_pairs")


def dark_codes() -> np.ndarray:
    todo("rishon.operators.dark_codes")


def inner_target(kind: str, alpha: float | None, beta: float | None, order: int = 1) -> np.ndarray:
    todo("rishon.operators.inner_target")


def closed_block(g2: float) -> np.ndarray:
    todo("rishon.operators.closed_block")


def closed_codes() -> tuple[int, int, np.ndarray]:
    todo("rishon.operators.closed_codes")


def det_term_inner() -> np.ndarray:
    todo("rishon.operators.det_term_inner")
