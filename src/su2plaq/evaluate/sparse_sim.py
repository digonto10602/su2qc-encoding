"""Sparse COO simulator (prompts/002 §2.7). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from su2plaq._stub import todo

SIM_BASIS = ["x", "z", "s", "sdg", "t", "tdg", "h", "sx", "rz", "p", "u", "cx", "cz", "cp", "swap", "ccx", "ccz", "unitary"]


@dataclass
class Batch:
    keys: np.ndarray
    cols: np.ndarray
    amps: np.ndarray
    n_qubits: int


class SimCapExceeded(RuntimeError):
    pass


def run_batch(qc, inputs: np.ndarray, cap: int = 5_000_000) -> Batch:
    todo("run_batch")


def encoded_block(batch: Batch, codes: np.ndarray, n_inputs: int, code_mask: int) -> tuple[np.ndarray, np.ndarray]:
    todo("encoded_block")
