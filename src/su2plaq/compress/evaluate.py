"""Program evaluation for the compression loop (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass

from su2plaq._stub import todo
from su2plaq.evaluate.evaluator import Verdict


@dataclass
class ProgramResult:
    valid: bool
    reason: str
    verdict: Verdict | None
    verdicts_alt: list
    skeleton_equal: bool
    metrics: dict | None
    program_sha256: str
    wall_s: float
    discoveries: list[str]
    summary: str


def load_program(path):
    todo("load_program")


def skeleton(qc) -> list[tuple]:
    todo("skeleton")


def evaluate_program(path, spec, mode: str = "full") -> ProgramResult:
    todo("evaluate_program")


def evaluate_circuit(qc, spec, mode: str = "full") -> ProgramResult:
    todo("evaluate_circuit")
