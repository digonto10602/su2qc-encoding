"""Task specification for the compression loop (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from su2plaq._stub import todo
from su2plaq.encodings.base import ALT_ANGLES


@dataclass
class TaskSpec:
    encoding: str
    kind: str
    alpha: float
    beta: float
    order: int = 1
    alt_angles: tuple = ALT_ANGLES
    tol_err: float = 1e-10
    tol_leak: float = 1e-12
    eps: float = 1e-6
    eval_budget_s: float = 300.0
    support_cap: int = 5_000_000
    max_qubits: int | None = None
    cell_k: int = 8
    trial_inputs: int = 64
    trial_seed: int = 0

    def sha256(self) -> str:
        todo("TaskSpec.sha256")

    def render(self) -> str:
        todo("TaskSpec.render")

    def write(self, path=None) -> pathlib.Path:
        todo("TaskSpec.write")

    def with_angles(self, alpha: float, beta: float) -> "TaskSpec":
        todo("TaskSpec.with_angles")


def default_spec(encoding: str = "twelve", kind: str = "step") -> TaskSpec:
    todo("default_spec")
