"""Rishon task spec, registered compress view, structure facts, spec text (prompts/203 section 3.1, 4).  STUBS (step 6.1)."""
from __future__ import annotations

import numpy as np

from su2plaq.rishon.compress._pending import pending

RISHON_NOMINAL = (0.37, 0.61)       # = encodings.rishon.RISHON_NOMINAL


def register() -> None:
    """NOMINAL_ANGLES["rishon"] = RISHON_NOMINAL; su2plaq.compress.spec._ENCODINGS["rishon"] = RishonCompressView() (idempotent)."""
    raise pending("spec.register", "6.1")


class RishonCompressView:
    """The encoding object the laptop machinery sees for "rishon" (duck-typed as prompts/002 section 2.7)."""

    name = "rishon"
    n_data = 16
    n_outer = 32
    is_basis_encoding = True

    def inner_codes(self) -> np.ndarray:
        raise pending("spec.RishonCompressView.inner_codes", "6.1")

    def physical_vectors(self):
        raise pending("spec.RishonCompressView.physical_vectors", "6.1")

    def target(self, kind, alpha, beta, order=1) -> np.ndarray:
        raise pending("spec.RishonCompressView.target", "6.1")

    def layout_of(self, qc):
        raise pending("spec.RishonCompressView.layout_of", "6.1")

    def decode_state(self, codes, amps):
        raise pending("spec.RishonCompressView.decode_state", "6.1")

    def describe(self) -> str:
        raise pending("spec.RishonCompressView.describe", "6.1")

    def import_map(self, source) -> str:
        raise pending("spec.RishonCompressView.import_map", "6.1")

    def bright_pairs(self) -> list:
        raise pending("spec.RishonCompressView.bright_pairs", "6.1")

    def heights(self, code: int) -> tuple:
        raise pending("spec.RishonCompressView.heights", "6.1")

    def closed_codes(self):
        raise pending("spec.RishonCompressView.closed_codes", "6.1")

    def dark_codes(self) -> np.ndarray:
        raise pending("spec.RishonCompressView.dark_codes", "6.1")


def rishon_spec(kind: str = "step", order: int = 1):
    """TaskSpec for the rishon encoding (same sha256 as the laptop default_spec("rishon", kind) after register())."""
    raise pending("spec.rishon_spec", "6.1")


def structure_facts() -> dict:
    raise pending("spec.structure_facts", "6.1")


def write_structure_json(path=None):
    raise pending("spec.write_structure_json", "6.1")


def render_spec(spec) -> str:
    raise pending("spec.render_spec", "6.1")


def write_spec(spec, path=None):
    raise pending("spec.write_spec", "6.1")
