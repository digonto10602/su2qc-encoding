"""48-qubit rishon circuits (prompts/200 §2.5; METHODS-rishon R7). Stubs (step 5.0); built in 5.6-5.8."""
from __future__ import annotations

from su2plaq._stub import todo

N_DATA, N_OUTER = 16, 32


def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False):
    todo("circuits.rishon.build_UE")


def build_UB(beta: float, with_outer: bool = False):
    todo("circuits.rishon.build_UB")


def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False):
    todo("circuits.rishon.build_step")


def pair_frames(beta: float) -> list[dict]:
    todo("circuits.rishon.pair_frames")
