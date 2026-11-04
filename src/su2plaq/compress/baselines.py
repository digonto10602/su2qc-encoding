"""Baselines and external seeds (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from su2plaq._stub import todo


def general_circuit(spec):
    todo("general_circuit")


def general_program_path(spec) -> pathlib.Path:
    todo("general_program_path")


def qiskit_l3(spec, seed: int = 12345):
    todo("qiskit_l3")


@dataclass
class SeedCircuit:
    qc: object
    source: str
    fixed_angle: bool
    alpha: float | None
    beta: float | None
    kind: str
    can_be_parent: bool


def import_seed(spec, source: str):
    todo("import_seed")


def evaluate_seed(spec, seed: SeedCircuit, mode: str = "full"):
    todo("evaluate_seed")
