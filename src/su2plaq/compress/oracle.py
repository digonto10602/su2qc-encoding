"""Exact-target oracle for proposers (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

import numpy as np

from su2plaq._stub import todo


def target(spec) -> np.ndarray:
    todo("oracle.target")


def column(spec, j, top: int = 20) -> list[tuple[int, complex]]:
    todo("oracle.column")


def element(spec, i, j) -> complex:
    todo("oracle.element")


def codec(spec) -> str:
    todo("oracle.codec")


def block(spec, outer_pattern: int) -> np.ndarray:
    todo("oracle.block")


def main(argv=None):
    todo("oracle CLI")


if __name__ == "__main__":
    main()
