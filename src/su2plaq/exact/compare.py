"""Route A vs route B comparison (prompts/002 §2.4). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def gauge_align(A, B, tol: float = 1e-9) -> tuple[np.ndarray | None, float]:
    todo("gauge_align")


def spectra_match(HE_A, HB_A, HE_B, HB_B, g2_list=(0.5, 1.0, 2.0)) -> float:
    todo("spectra_match")


def outer_block_structure(HB_phys, basis, K=None) -> dict:
    todo("outer_block_structure")
