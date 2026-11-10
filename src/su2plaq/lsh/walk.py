"""Skeleton language of the LSH circuits (prompts/400 section 2). STUB (step 7.0): every function raises NotImplementedError
until step 7.4 (coupling_table, partner_table) and 7.6 (the rest).

Step = ("cx", c, t) | ("x", q) | ("h", q) | ("rccx", a, b, t) | ("rz", q) | ("p_alpha", q); wires: data 0..11, ancillas 12..
"""
from __future__ import annotations

LINK = (0, 3, 6, 9)        # after transcoding: j_b, j_r, j_t, j_l
CBIT = (1, 4, 7, 10)       # after transcoding: [J_c = 1]
WBIT = (2, 5, 8, 11)       # after transcoding: w_c = N_v mod 2
TARGET = LINK[0]
J_HALF_PHASE = 0.75
TRANSCODE: tuple = ()      # filled at step 7.6
FRAME: tuple = ()          # filled at step 7.6


def _pending(name: str, step: str):
    raise NotImplementedError(f"PENDING: su2plaq.lsh.walk.{name} is not built yet (prompts/400 step {step})")


def transcode_steps() -> list:
    _pending("transcode_steps", "7.6")


def mirror(steps) -> list:
    _pending("mirror", "7.6")


def skeleton(electric: int = 0) -> tuple:
    _pending("skeleton", "7.6")


def classical_run(steps, code: int) -> int:
    _pending("classical_run", "7.6")


def classical_slots(steps, code: int) -> list:
    _pending("classical_slots", "7.6")


def coupling_table(enc) -> dict:
    _pending("coupling_table", "7.4")


def partner_table(enc) -> dict:
    _pending("partner_table", "7.4")


def solve_angles(steps, table, beta):
    _pending("solve_angles", "7.6")


def angle_fractions(steps, table, max_den: int = 64) -> list:
    _pending("angle_fractions", "7.6")


def build(steps, n_anc, table, alpha, beta, order=1, with_outer=False, name="UB"):
    _pending("build", "7.6")
