"""Rishon physical space: corner kernels, basis, counts, Gauss residuals (prompts/200 §2.2; METHODS-rishon R3).
Stubs (step 5.0); built in step 5.2."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from su2plaq._stub import todo
from su2plaq.geometry import Diagram

LINK_TYPES = ("A", "B", "Q")
N_QUBITS = 48
N_DATA = 16
N_OUTER = 32


def near_shift(link: int) -> int:
    todo("rishon.physical.near_shift")


def far_shift(link: int) -> int:
    todo("rishon.physical.far_shift")


def corner_kernel(types_roles: tuple[tuple[str, str], ...]):
    todo("rishon.physical.corner_kernel")


@dataclass
class RishonBasis:
    diagram: Diagram
    labels: list
    keys: list
    amps: list
    dim: int

    def index(self, label) -> int:
        todo("RishonBasis.index")

    @staticmethod
    def inner_key(keys) -> np.ndarray:
        todo("RishonBasis.inner_key")

    @staticmethod
    def outer_key(keys) -> np.ndarray:
        todo("RishonBasis.outer_key")

    def u1_charges(self, k: int) -> tuple[int, int, int, int]:
        todo("RishonBasis.u1_charges")


def rishon_basis() -> RishonBasis:
    todo("rishon.physical.rishon_basis")


def count_by_fusion() -> dict:
    todo("rishon.physical.count_by_fusion")


def counts(basis) -> dict:
    todo("rishon.physical.counts")


def closed_indices(basis) -> list[int]:
    todo("rishon.physical.closed_indices")


def sample_indices(basis, n: int = 256, seed: int = 20261104) -> list[int]:
    todo("rishon.physical.sample_indices")


def gauss_residuals_coo(keys_list, amps_list) -> np.ndarray:
    todo("rishon.physical.gauss_residuals_coo")


def gauss_residual(keys, amps) -> float:
    todo("rishon.physical.gauss_residual")


def inner_span(basis) -> np.ndarray:
    todo("rishon.physical.inner_span")


def inner_span_rank_by_corners() -> int:
    todo("rishon.physical.inner_span_rank_by_corners")
