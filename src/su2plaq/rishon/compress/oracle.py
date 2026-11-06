"""Rishon oracle for humans and proposer sessions (prompts/203 section 3.1).  STUBS (step 6.1)."""
from __future__ import annotations

import numpy as np

from su2plaq.rishon.compress._pending import pending


def target(spec) -> np.ndarray:
    raise pending("oracle.target", "6.1")


def column(spec, j, top=20):
    raise pending("oracle.column", "6.1")


def element(spec, i, j):
    raise pending("oracle.element", "6.1")


def codec(spec, state=None) -> str:
    raise pending("oracle.codec", "6.1")


def pairs(spec, which: str = "all") -> list:
    raise pending("oracle.pairs", "6.1")


def closed_block(spec) -> np.ndarray:
    raise pending("oracle.closed_block", "6.1")


def main(argv=None) -> int:
    raise pending("oracle.main", "6.1")


if __name__ == "__main__":
    raise SystemExit(main())
