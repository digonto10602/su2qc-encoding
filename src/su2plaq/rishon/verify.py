"""Rishon verification on the inner view + sampled Gauss check (prompts/200 §2.6). Stubs (step 5.0); built in 5.5."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from su2plaq._stub import todo
from su2plaq.evaluate.evaluator import Verdict, synth_tolerances  # noqa: F401  (re-export)


@dataclass
class RishonVerdict:
    ok: bool
    reason: str
    certified: bool
    op_norm_error: float
    block_error: float
    leak_amplitude: float
    dropped_total: float
    max_leak: float
    dirty_ancilla: float
    phase: complex
    gauss_residual: float
    gauss_states: int
    outer_bits_read: int
    method: str
    engine: str
    seconds: float
    tolerances: dict
    failing_inputs: list
    inner_verdict: Verdict | None
    extra: dict = field(default_factory=dict)


def verify(qc, enc, kind: str, alpha: float | None, beta: float | None, order: int = 1, *, tol_err: float = 1e-10,
           tol_gauss: float | None = None, gauss: bool = True, gauss_sample: int = 256, seed: int = 20261104,
           engine: str = "auto", cap: int = 5_000_000, target: np.ndarray | None = None) -> RishonVerdict:
    todo("rishon.verify.verify")


def physical_cross_check(qc, enc, kind, alpha, beta, order=1, states: list[int] | None = None) -> dict:
    todo("rishon.verify.physical_cross_check")
