"""Rishon inner operators on the 1296 valid 16-bit codes (prompts/200 §2.3; METHODS-rishon R4).
Stubs (step 5.0); built in step 5.3 (`inner_codes` already built in step 5.2 for the inner span)."""
from __future__ import annotations

import itertools

import numpy as np

from su2plaq._stub import todo
from su2plaq.rishon.algebra import RishonLink


def inner_codes() -> np.ndarray:
    """Sorted int64 16-bit data codes with two rishons on each of the four inner links (6^4 = 1296)."""
    sector = RishonLink().sector
    codes = [sum(int(s) << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(sector, repeat=4)]
    return np.array(sorted(codes), dtype=np.int64)


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
