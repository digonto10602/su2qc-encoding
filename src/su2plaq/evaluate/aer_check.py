"""Qiskit-Aer cross-check engines (prompts/002 §2.7). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def aer_statevector_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int) -> tuple[np.ndarray, np.ndarray]:
    todo("aer_statevector_block")


def aer_mps_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int, bond_dim: int | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    todo("aer_mps_block")
