"""Encoding protocol (prompts/002 §2.5). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np

from su2plaq._stub import todo

if TYPE_CHECKING:
    from qiskit import QuantumCircuit
    from su2plaq.exact.physical import PhysicalBasis

NOMINAL_ANGLES = {"twelve": (0.37, 0.61)}
ALT_ANGLES = ((0.91, 0.23), (1.70, 1.00))


@dataclass
class Layout:
    data: list[int]
    outer: list[int]
    ancilla: list[int]


@dataclass
class EncodedBasis:
    codes: list[np.ndarray]
    amps: list[np.ndarray]
    n_data: int
    n_outer: int


class Encoding(Protocol):
    name: str
    n_data: int
    n_outer: int
    registers: dict[str, list[int]]
    is_basis_encoding: bool
    basis: "PhysicalBasis"

    def inner_codes(self) -> np.ndarray: ...

    def physical_vectors(self) -> EncodedBasis: ...

    def decode(self, code: int) -> int | None: ...

    def target(self, kind: str, alpha: float, beta: float, order: int = 1) -> np.ndarray: ...

    def layout_of(self, qc: "QuantumCircuit") -> Layout: ...

    def describe(self) -> str: ...

    def import_map(self, source: str) -> dict | str: ...
