"""Rishon oracle for humans and proposer sessions (prompts/203 section 3.1).  Programs use `su2plaq.compress.oracle` with
`get_encoding("rishon")`; this module is the same oracle with rishon-specific extras (pair listing, closed block, codec).

    python -m su2plaq.rishon.compress.oracle [--kind step|UB|UE] [--alpha a --beta b --order o] [--column j] [--element i j]
        [--codec [--state k]] [--pairs [--closed]] [--block]

States are the 1296 inner codes in sorted code order (an integer index, or a 1-tuple `(code,)`).
"""
from __future__ import annotations

import argparse

import numpy as np

import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)
from su2plaq.compress import oracle as _lap
from su2plaq.compress.spec import TaskSpec, get_encoding
from su2plaq.rishon import operators as _ops
from su2plaq.rishon.compress.spec import rishon_spec

_ZERO = 1e-14


def _index(spec, s) -> int:
    enc = get_encoding(spec.encoding)
    if isinstance(s, (int, np.integer)):
        if not 0 <= int(s) < len(enc.basis.labels):
            raise IndexError(f"state index {s} out of range")
        return int(s)
    return enc.basis.index(s)


def target(spec) -> np.ndarray:
    """The exact 1296 x 1296 inner operator V_in (read-only; copy before modifying)."""
    return _lap.target(spec)


def column(spec, j, top=20):
    """Largest entries (row index, value) of target column j, sorted by |value| descending; entries below 1e-14 dropped."""
    col = target(spec)[:, _index(spec, j)]
    rows = [int(r) for r in np.argsort(-np.abs(col), kind="stable") if abs(col[r]) > _ZERO]
    return [(r, complex(col[r])) for r in rows[:top]]


def element(spec, i, j):
    return complex(target(spec)[_index(spec, i), _index(spec, j)])


def codec(spec, state=None) -> str:
    """Register / codec description; with `state`, the computational basis state (code as a bit string, qubit 0 rightmost) and the
    link types (b, r, t, l) of that inner code."""
    enc = get_encoding(spec.encoding)
    text = enc.describe()
    if state is not None:
        k = _index(spec, state)
        code = enc.basis.labels[k][0]
        types = _ops._types(code)
        text += (f"\nState {k}: code {code} = {code:016b} (qubit 15 ... qubit 0), amplitude 1; links b r t l = "
                 f"{' '.join(types)} (link l occupies bits 4l..4l+3).\n")
    return text


def pairs(spec, which: str = "all") -> list:
    """[{"index", "kappa", "u": [(code, amp)], "v": [(code, amp)]}] sorted as operators.bright_pairs(); which in {"all", "closed"}
    ("closed" = the pairs that touch the closed-plaquette states: vac_A, vac_B or the loop state)."""
    if which not in ("all", "closed"):
        raise ValueError(f"which must be 'all' or 'closed', got {which!r}")
    codes = get_encoding(spec.encoding).inner_codes()
    va, vb, loop = _ops.closed_codes()
    closed = {int(va), int(vb)} | {int(c) for c in loop}
    out = []
    for i, (u, v, k) in enumerate(_ops.bright_pairs()):
        su, sv = np.flatnonzero(np.abs(u) > 0), np.flatnonzero(np.abs(v) > 0)
        d = {"index": i, "kappa": float(k), "u": [(int(codes[a]), float(u[a])) for a in su], "v": [(int(codes[a]), float(v[a])) for a in sv]}
        if which == "closed" and not ({c for c, _ in d["u"]} | {c for c, _ in d["v"]}) & closed:
            continue
        out.append(d)
    return out


def closed_block(spec) -> np.ndarray:
    """3 x 3 block of the target on (vac_A, loop, vac_B): B V B^T with real orthonormal rows (loop ~ W vac_A, positive)."""
    codes = get_encoding(spec.encoding).inner_codes()
    va, vb, _ = _ops.closed_codes()
    ia, ib = int(np.searchsorted(codes, va)), int(np.searchsorted(codes, vb))
    col = np.real(_ops.plaquette_W_inner()[:, ia])
    B = np.zeros((3, len(codes)))
    B[0, ia] = 1.0
    B[1] = col / np.linalg.norm(col)
    B[2, ib] = 1.0
    return (B @ target(spec) @ B.T).astype(np.complex128)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.rishon.compress.oracle")
    ap.add_argument("--kind", "--target", dest="kind", default="step", help="step | UB | UE (case-insensitive)")
    ap.add_argument("--alpha", type=float)
    ap.add_argument("--beta", type=float)
    ap.add_argument("--order", type=int, default=1)
    ap.add_argument("--column", type=int)
    ap.add_argument("--element", type=int, nargs=2, metavar=("I", "J"))
    ap.add_argument("--codec", action="store_true")
    ap.add_argument("--state", type=int, help="with --codec: show this state's code")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--closed", action="store_true", help="with --pairs: only the pairs touching the closed sector")
    ap.add_argument("--block", action="store_true", help="the 3x3 closed block on (vac_A, loop, vac_B)")
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args(argv)
    kind = {"step": "step", "ub": "UB", "ue": "UE"}[a.kind.lower()]
    spec = rishon_spec(kind, a.order)
    if a.alpha is not None or a.beta is not None:
        spec = spec.with_angles(a.alpha if a.alpha is not None else spec.alpha, a.beta if a.beta is not None else spec.beta)
    if a.codec:
        print(codec(spec, a.state))
    if a.column is not None:
        for r, v in column(spec, a.column, a.top):
            print(f"row {r:4d}  {v.real:+.12f}{v.imag:+.12f}j  |.|={abs(v):.12f}")
    if a.element is not None:
        print(f"{element(spec, *a.element):.15f}")
    if a.pairs:
        for p in pairs(spec, "closed" if a.closed else "all"):
            fmt = lambda vec: " ".join(f"{c}:{x:+.6f}" for c, x in vec)
            print(f"pair {p['index']:2d} kappa={p['kappa']:.12f}  u[{fmt(p['u'])}]  v[{fmt(p['v'])}]")
    if a.block:
        np.set_printoptions(precision=8, suppress=True, linewidth=160)
        print(closed_block(spec))
    if not (a.codec or a.column is not None or a.element is not None or a.pairs or a.block):
        V = target(spec)
        print(f"target {spec.kind} order {spec.order} alpha={spec.alpha:g} beta={spec.beta:g}: {V.shape[0]}x{V.shape[1]} unitary, "
              f"|U^dag U - 1| = {np.abs(V.conj().T @ V - np.eye(len(V))).max():.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
