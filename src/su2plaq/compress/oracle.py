"""Exact-target oracle for proposers (prompts/002 §2.10).  Programs may import this module (emission-time classical
computation is allowed): angles are solved from the operator, not typed in.

    python -m su2plaq.compress.oracle --encoding twelve --kind step|UB|UE [--column j] [--element i j] [--codec]
                                       [--block o] [--top 20]

States are indexed in the order of `PhysicalBasis.labels` (route A, CG label ((j_0..j_11), (J_0..J_3))); a state may be given
as its integer index or as its label tuple.
"""
from __future__ import annotations

import argparse
import functools

import numpy as np

from su2plaq.compress.spec import TaskSpec, get_encoding

_ZERO = 1e-14


def _index(spec, s) -> int:
    enc = get_encoding(spec.encoding)
    if isinstance(s, (int, np.integer)):
        if not 0 <= int(s) < len(enc.basis.labels):
            raise IndexError(f"state index {s} out of range")
        return int(s)
    key = (tuple(float(x) for x in s[0]), tuple(float(x) for x in s[1]))
    return enc.basis.index(key)


@functools.lru_cache(maxsize=16)
def _target_cached(encoding, kind, alpha, beta, order):
    V = get_encoding(encoding).target(kind, alpha, beta, order)
    V.setflags(write=False)
    return V


def target(spec: TaskSpec) -> np.ndarray:
    """The exact D x D target in physical-basis order (read-only; copy before modifying)."""
    return _target_cached(spec.encoding, spec.kind, float(spec.alpha), float(spec.beta), int(spec.order))


def column(spec: TaskSpec, j, top: int = 20) -> list[tuple[int, complex]]:
    """Largest entries (row index, value) of target column j, sorted by |value| descending; entries below 1e-14 dropped."""
    col = target(spec)[:, _index(spec, j)]
    rows = [int(r) for r in np.argsort(-np.abs(col), kind="stable") if abs(col[r]) > _ZERO]
    return [(r, complex(col[r])) for r in rows[:top]]


def element(spec: TaskSpec, i, j) -> complex:
    return complex(target(spec)[_index(spec, i), _index(spec, j)])


def codec(spec: TaskSpec, state=None) -> str:
    """Register / codec description of the encoding; with `state`, the computational-basis support of that physical state
    (code as a bit string with qubit 0 rightmost, amplitude)."""
    enc = get_encoding(spec.encoding)
    text = enc.describe()
    text += ("\nState indexing: physical states are numbered in the order of the route-A labels "
             "((j_0..j_11), (J_0..J_3)); links 0-3 = b r t l, 4-11 = outer links o0..o7.\n")
    if state is not None:
        k = _index(spec, state)
        eb = enc.physical_vectors()
        n = eb.n_data + eb.n_outer
        order = np.argsort(-np.abs(eb.amps[k]), kind="stable")
        lab = enc.basis.labels[k]
        text += f"\nState {k}, label {lab}: {len(order)} computational-basis components (qubit {n - 1} ... qubit 0):\n"
        for t in order[:40]:
            text += f"  {int(eb.codes[k][t]):0{n}b}  {complex(eb.amps[k][t]):.6f}\n"
        if len(order) > 40:
            text += f"  ... {len(order) - 40} more\n"
    return text


def block(spec: TaskSpec, outer_pattern: int) -> np.ndarray:
    """Unitary block of the target on the physical states that share the outer SPIN configuration of the outer electric
    pattern `outer_pattern` (outer key: sum_l s_l 5^l over outer links; s_l = 0 means j = 0). Pattern 0 is the closed plaquette
    (2 x 2). The target is block diagonal in the outer spins, so each block is unitary."""
    enc = get_encoding(spec.encoding)
    spins = []
    key = int(outer_pattern)
    for _ in range(8):
        key, s = divmod(key, 5)
        spins.append(0.0 if s == 0 else 0.5)
    if key:
        raise ValueError(f"outer pattern {outer_pattern} is not a valid outer key")
    sel = [k for k, (j, _J) in enumerate(enc.basis.labels) if tuple(j[4:]) == tuple(spins)]
    if not sel:
        raise ValueError(f"no physical state has outer spins {tuple(spins)}")
    return target(spec)[np.ix_(sel, sel)].copy()


def main(argv=None):
    from su2plaq.compress.spec import default_spec

    ap = argparse.ArgumentParser(prog="python -m su2plaq.compress.oracle")
    ap.add_argument("--encoding", default="twelve")
    ap.add_argument("--kind", "--target", dest="kind", default="step", help="step | UB | UE (case-insensitive)")
    ap.add_argument("--alpha", type=float)
    ap.add_argument("--beta", type=float)
    ap.add_argument("--order", type=int, default=1)
    ap.add_argument("--column", type=int)
    ap.add_argument("--element", type=int, nargs=2, metavar=("I", "J"))
    ap.add_argument("--codec", action="store_true")
    ap.add_argument("--state", type=int, help="with --codec: show this state's computational-basis support")
    ap.add_argument("--block", type=int, metavar="O")
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args(argv)
    kind = {"step": "step", "ub": "UB", "ue": "UE"}[a.kind.lower()]
    spec = default_spec(a.encoding, kind)
    if a.alpha is not None or a.beta is not None:
        spec = spec.with_angles(a.alpha if a.alpha is not None else spec.alpha, a.beta if a.beta is not None else spec.beta)
    spec = TaskSpec(**{**spec.to_dict(), "order": a.order})
    if a.codec:
        print(codec(spec, a.state))
    if a.column is not None:
        for r, v in column(spec, a.column, a.top):
            print(f"row {r:4d}  {v.real:+.12f}{v.imag:+.12f}j  |.|={abs(v):.12f}")
    if a.element is not None:
        print(f"{element(spec, *a.element):.15f}")
    if a.block is not None:
        np.set_printoptions(precision=8, suppress=True, linewidth=160)
        print(block(spec, a.block))
    if not (a.codec or a.column is not None or a.element is not None or a.block is not None):
        V = target(spec)
        print(f"target {spec.kind} order {spec.order} alpha={spec.alpha:g} beta={spec.beta:g}: {V.shape[0]}x{V.shape[1]} unitary, "
              f"|U^dag U - 1| = {np.abs(V.conj().T @ V - np.eye(len(V))).max():.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
