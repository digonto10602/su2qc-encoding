"""Skeleton language of the LSH circuits (prompts/400 section 2; docs/METHODS-lsh.md L7).

Step = ("cx", c, t) | ("x", q) | ("h", q) | ("rccx", a, b, t) | ("rz", q) | ("p_alpha", q); wires: data 0..11, ancillas 12..
(relabelled after the outer register when with_outer).  Rotation angles are solved from the LSH coupling table at build
time (Walsh series, least squares on the 47 inner codes), never typed in."""
from __future__ import annotations

from fractions import Fraction

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

LINK = (0, 3, 6, 9)        # after transcoding: j_b, j_r, j_t, j_l (wire l_pn of sites c0..c3 holds N_n(c) = 2 j_n(c))
CBIT = (1, 4, 7, 10)       # after transcoding: [J_c = 1]
WBIT = (2, 5, 8, 11)       # after transcoding: w_c = N_v mod 2 = [J_c = 1/2]
TARGET = LINK[0]
J_HALF_PHASE = 0.75
_A, _B, _F, _P, _Q, _G1, _G2 = range(12, 19)


def transcode_steps() -> list:
    """In place per 'in' site (x, y, z) = (l_pn, l_nv, l_vp): cx(y, z): z <- w; cx(y, x): x <- N_n; rccx(z, x, y): y <- [J = 1]."""
    st = []
    for c in range(4):
        x, y, z = 3 * c, 3 * c + 1, 3 * c + 2
        st += [("cx", y, z), ("cx", y, x), ("rccx", z, x, y)]
    return st


TRANSCODE: tuple = tuple(transcode_steps())
FRAME: tuple = (("cx", LINK[1], LINK[3]), ("cx", LINK[0], LINK[1]), ("cx", LINK[0], LINK[2]))


def mirror(steps) -> list:
    """Uncompute: reversed, rotations dropped (cx, x, h, rccx are self-inverse)."""
    return [s for s in reversed(steps) if s[0] not in ("rz", "p_alpha")]


def _flags() -> list:
    m1, m2, m3 = LINK[1], LINK[2], LINK[3]
    return ([("x", q) for q in CBIT] + [("rccx", CBIT[0], CBIT[1], _A), ("rccx", CBIT[2], CBIT[3], _B), ("rccx", _A, _B, _F),
                                        ("x", m2), ("x", m3), ("rccx", m2, m3, _P), ("rccx", _F, _P, _Q),
                                        ("x", m1), ("rccx", _Q, m1, _G1), ("x", m1), ("rccx", _Q, m1, _G2)])


def skeleton(electric: int = 0) -> tuple:
    """(steps, n_anc) of U_B (electric = 0), the order-1 step (1: electric layer first) or the order-2 step (2): transcoder;
    [electric layer on the link wires]; frame; h; flags; 4-rotation walk; flags^-1; h; frame^-1; [electric layer];
    transcoder^-1."""
    if electric not in (0, 1, 2):
        raise ValueError("electric must be 0, 1 or 2")
    pre = list(TRANSCODE)
    el = [("p_alpha", q) for q in LINK]
    flags = _flags()
    walk = [("rz", TARGET)]
    for w in (_F, _G1, _G2):
        walk += [("cx", w, TARGET), ("rz", TARGET), ("cx", w, TARGET)]
    core = list(FRAME) + [("h", TARGET)] + flags + walk + mirror(flags) + [("h", TARGET)] + mirror(FRAME)
    return pre + (el if electric else []) + core + (el if electric == 2 else []) + mirror(pre), 7


def classical_run(steps, code: int) -> int:
    """Bit pattern after the classical gates of `steps` (Toffoli semantics for rccx; h, rz, p_alpha skipped)."""
    x = int(code)
    for st in steps:
        op = st[0]
        if op == "cx":
            if (x >> st[1]) & 1:
                x ^= 1 << st[2]
        elif op == "x":
            x ^= 1 << st[1]
        elif op == "rccx":
            if (x >> st[1]) & 1 and (x >> st[2]) & 1:
                x ^= 1 << st[3]
        elif op not in ("h", "rz", "p_alpha"):
            raise ValueError(f"unknown step {st!r}")
    return x


def classical_slots(steps, code: int) -> list:
    """Bit of the rz wire at every rz for inner code `code`; the walk target is cleared at the first h (its value there is
    the pair member, which the slot must not depend on)."""
    x = int(code)
    slots, seen_h = [], False
    for st in steps:
        op = st[0]
        if op == "h":
            if not seen_h:
                x &= ~(1 << st[1])
                seen_h = True
            else:
                break
        elif op == "rz":
            slots.append((x >> st[1]) & 1)
        else:
            x = classical_run([st], x)
    return slots


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



def _system(steps, table):
    codes = sorted(table)
    A = np.array([[(-1.0) ** v for v in classical_slots(steps, c)] for c in codes])
    return A, np.array([table[c] for c in codes])


def solve_angles(steps, table, beta: float):
    A, k = _system(steps, table)
    b = 2.0 * beta * k
    theta, *_ = np.linalg.lstsq(A, b, rcond=None)
    return theta, float(np.abs(A @ theta - b).max())


def angle_fractions(steps, table, max_den: int = 64) -> list:
    theta, _ = solve_angles(steps, table, 1.0)
    fr = [Fraction(float(t)).limit_denominator(max_den) for t in theta]
    A, k = _system(steps, table)
    res = float(np.abs(A @ np.array([float(f) for f in fr]) - 2.0 * k).max())
    if res > 1e-12:
        raise ValueError(f"angles are not rational with denominator <= {max_den} (residual {res:.2e})")
    return fr


def build(steps, n_anc: int, table, alpha, beta: float, order: int = 1, with_outer: bool = False, name: str = "UB"):
    """QuantumCircuit (registers d[12], [o[12]], a[n_anc]) of a step list; rz angles solved from `table` (ValueError if the
    skeleton cannot reproduce it, residual > 1e-9); p_alpha = p(-3 alpha/4) (order 1) or p(-3 alpha/8) (order 2)."""
    theta, res = solve_angles(steps, table, beta)
    if res > 1e-9:
        raise ValueError(f"skeleton does not reproduce the coupling table: residual {res:.2e}")
    angles = iter(theta)
    regs = [QuantumRegister(12, "d")] + ([QuantumRegister(12, "o")] if with_outer else []) + ([QuantumRegister(n_anc, "a")] if n_anc else [])
    qc = QuantumCircuit(*regs, name=name)
    off = 24 if with_outer else 12

    def Q(i):
        return i if i < 12 else off + (i - 12)

    for st in steps:
        op = st[0]
        if op == "cx":
            qc.cx(Q(st[1]), Q(st[2]))
        elif op == "x":
            qc.x(Q(st[1]))
        elif op == "h":
            qc.h(Q(st[1]))
        elif op == "rccx":
            qc.rccx(Q(st[1]), Q(st[2]), Q(st[3]))
        elif op == "rz":
            qc.rz(float(next(angles)), Q(st[1]))
        elif op == "p_alpha":
            if alpha is None:
                raise ValueError("skeleton has an electric layer but alpha is None")
            qc.p(-J_HALF_PHASE * (alpha if order == 1 else alpha / 2), Q(st[1]))
        else:
            raise ValueError(f"unknown step {st!r}")
    return qc
