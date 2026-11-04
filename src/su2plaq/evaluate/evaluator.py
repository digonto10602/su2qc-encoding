"""Circuit evaluator (prompts/002 §2.7). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from su2plaq._stub import todo
from su2plaq.encodings.base import Layout


class OuterWriteError(ValueError):
    pass


def classify_outer_gates(qc, layout: Layout) -> set[int]:
    todo("classify_outer_gates")


def specialise(qc, read_qubits: set[int], pattern: int):
    todo("specialise")


@dataclass
class Verdict:
    ok: bool
    reason: str
    op_norm_error: float
    max_leak: float
    dirty_ancilla: float
    phase: complex
    outer_bits_read: int
    n_blocks: int
    gauss_residual: float
    method: str
    engine: str
    seconds: float
    failing_inputs: list
    n_inputs: int


def evaluate(qc, enc, target: np.ndarray, *, tol_err: float = 1e-10, tol_leak: float = 1e-12, gauss: bool = True,
             method: str = "auto", engine: str = "auto") -> Verdict:
    todo("evaluate")


def inner_target(enc, kind, alpha, beta, order=1) -> np.ndarray:
    todo("inner_target")
