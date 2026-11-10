"""Skeleton language of the LSH circuits (prompts/400 section 2). STUB (step 7.0): every function raises NotImplementedError
until step 7.4 (coupling_table, partner_table) and 7.6 (the rest).

Step = ("cx", c, t) | ("x", q) | ("h", q) | ("rccx", a, b, t) | ("rz", q) | ("p_alpha", q); wires: data 0..11, ancillas 12..
"""
from __future__ import annotations

import numpy as np

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
    """inner code -> K[partner, code] (0.0 for dark codes), snapped to half-integers; ValueError unless K is a matching."""
    codes = enc.inner_codes().tolist()
    K = np.asarray(enc.K_codes)
    table = {}
    for i, c in enumerate(codes):
        nz = np.flatnonzero(np.abs(K[:, i]) > 1e-12)
        if len(nz) == 0:
            table[c] = 0.0
            continue
        if len(nz) != 1:
            raise ValueError(f"K is not a pair matching at inner code {c:012b}")
        v = float(K[nz[0], i])
        if abs(2 * v - round(2 * v)) > 1e-12:
            raise ValueError(f"K at inner code {c:012b} is {v!r}, not a half-integer")
        table[c] = round(2 * v) / 2
    return table


def partner_table(enc) -> dict:
    """bright inner code -> the inner code the plaquette moves it to (K is a matching)."""
    codes = enc.inner_codes().tolist()
    K = np.asarray(enc.K_codes)
    out = {}
    for i, c in enumerate(codes):
        nz = np.flatnonzero(np.abs(K[:, i]) > 1e-12)
        if len(nz) > 1:
            raise ValueError(f"K is not a pair matching at inner code {c:012b}")
        if len(nz) == 1:
            out[c] = codes[int(nz[0])]
    return out


def solve_angles(steps, table, beta):
    _pending("solve_angles", "7.6")


def angle_fractions(steps, table, max_den: int = 64) -> list:
    _pending("angle_fractions", "7.6")


def build(steps, n_anc, table, alpha, beta, order=1, with_outer=False, name="UB"):
    _pending("build", "7.6")
