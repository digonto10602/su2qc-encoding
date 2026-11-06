"""Rishon (SU(2) quantum link model) encoding, 48 qubits (prompts/200 §2.4; METHODS-rishon R2).
Stubs (step 5.0); built in step 5.4.  M5 must not import su2plaq.compress.*."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from su2plaq._stub import todo
from su2plaq.encodings.base import EncodedBasis, Encoding, Layout  # noqa: F401

if TYPE_CHECKING:
    from su2plaq.rishon.physical import RishonBasis

RISHON_NOMINAL = (0.37, 0.61)    # NOT in encodings/base.NOMINAL_ANGLES (laptop-owned file)

_LINK_NAMES = ("b", "r", "t", "l")


def _registers() -> dict[str, list[int]]:
    regs = {"d": list(range(16)), "o": list(range(16, 48))}
    for l, nm in enumerate(_LINK_NAMES):
        regs[f"link_{nm}"] = list(range(4 * l, 4 * l + 4))
    for k in range(8):
        regs[f"outer_{k}"] = list(range(16 + 4 * k, 20 + 4 * k))
    return regs


class RishonEncoding(Encoding):
    name = "rishon"
    n_data = 16
    n_outer = 32
    is_basis_encoding = False

    def __init__(self):
        self.registers = _registers()
        self.basis: "RishonBasis | None" = None     # built lazily in step 5.4 (rishon_basis())

    def inner_codes(self) -> np.ndarray:
        todo("RishonEncoding.inner_codes")

    def physical_vectors(self, which: str = "all", n_sample: int = 256, seed: int = 20261104) -> EncodedBasis:
        todo("RishonEncoding.physical_vectors")

    def decode(self, code: int):
        todo("RishonEncoding.decode")

    def decode_state(self, codes, amps):
        todo("RishonEncoding.decode_state")

    def inner_target(self, kind, alpha, beta, order=1) -> np.ndarray:
        todo("RishonEncoding.inner_target")

    def target(self, kind, alpha, beta, order=1, states: list[int] | None = None) -> np.ndarray:
        todo("RishonEncoding.target")

    def inner_view(self) -> "RishonInnerView":
        todo("RishonEncoding.inner_view")

    def layout_of(self, qc) -> Layout:
        todo("RishonEncoding.layout_of")

    def describe(self) -> str:
        todo("RishonEncoding.describe")

    def import_map(self, source):
        todo("RishonEncoding.import_map")


class RishonInnerView:
    """Encoding-like object for the laptop evaluator (prompts/002 §2.7 duck typing)."""

    name = "rishon_inner"
    n_data = 16
    n_outer = 32
    is_basis_encoding = True

    def __init__(self):
        self.registers = _registers()

    def inner_codes(self) -> np.ndarray:
        todo("RishonInnerView.inner_codes")

    def physical_vectors(self) -> EncodedBasis:
        todo("RishonInnerView.physical_vectors")

    def layout_of(self, qc) -> Layout:
        todo("RishonInnerView.layout_of")

    def decode_state(self, codes, amps):
        todo("RishonInnerView.decode_state")
