"""Exact arithmetic for the Lean certificates (prompts/006 §5).  Skeleton: filled in by step 2.L4."""
from __future__ import annotations

from fractions import Fraction

from su2plaq._stub import todo


class KNum:
    """Element of the exact coefficient field K (eight rational components a..h)."""
    a: Fraction; b: Fraction; c: Fraction; d: Fraction; e: Fraction; f: Fraction; g: Fraction; h: Fraction

    def __init__(self, *args, **kwargs):
        todo("lean.exact.KNum")

    def to_complex(self) -> complex:
        todo("lean.exact.KNum.to_complex")

    def to_json(self) -> list[str]:
        todo("lean.exact.KNum.to_json")

    @staticmethod
    def recognise(z: complex, tol: float = 1e-12) -> "KNum | None":
        todo("lean.exact.KNum.recognise")


class Laurent(dict):
    """Laurent polynomial in (z_alpha, z_beta): dict[(int, int), KNum]."""

    def evaluate(self, theta_alpha: float, theta_beta: float) -> complex:
        todo("lean.exact.Laurent.evaluate")

    def to_json(self):
        todo("lean.exact.Laurent.to_json")


def rational_multiple(theta: float, base: float, max_den: int = 64, tol: float = 1e-12) -> Fraction | None:
    todo("lean.exact.rational_multiple")


def exact_corner_singlets(js, roles) -> list[list[KNum]]:
    todo("lean.exact.exact_corner_singlets")


def exact_physical_basis(convention: str = "cg") -> list[dict]:
    todo("lean.exact.exact_physical_basis")


def exact_link_U() -> list[list[list[list[KNum]]]]:
    todo("lean.exact.exact_link_U")


def exact_target_blocks(kind: str, order: int) -> list[dict]:
    todo("lean.exact.exact_target_blocks")
