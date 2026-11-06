"""Vendored su2qc-trotter `spinnet_v2` skeletons (prompts/100 §1.6, step 3.6).

SOURCE records where the skeleton lists come from.  Only the combinatorial structure (frame, flag computations, walk
masks) is copied; the rotation angles are NOT copied: `spinnet.walk.build_walk` re-solves them from our coupling table
(route-B gauge), exactly and linearly in beta.  su2qc-trotter itself is never imported.

Language differences to the sibling: its `rccx_dg` is written `rccx` here because Qiskit's RCCXGate is Hermitian (hence
self-inverse; checked by the unit tests); `rc3x` / `rc3x_dg` stay distinct (RC3XGate is not self-inverse) and are expanded
to basis gates by `build_walk(..., expand=True)`.  Wires: data 0..7 (links 0..3, corners 4..7), ancillas 8..10.
"""
from __future__ import annotations

from su2plaq.spinnet.walk import FRAME, TARGET, mirror

SOURCE = ("su2qc-trotter spinnet_v2: /home/digimonk/Projects/su2qc-trotter/src/su2trotter/designs/spinnet_v2.py "
          "(sibling checkout ~/Projects/siblings/su2qc-trotter/src/su2trotter/designs/spinnet_v2.py); "
          "sibling results commit feadc42 (docs/compression/results_spinnet_v2.json, 2026-10-28); "
          "skeleton lists vendored, rccx_dg written as rccx (self-inverse), angles re-solved from our K in route-B gauge")

FRAME_B = ((3, 1), (0, 3), (0, 2))          # q1 = l1^l3, q2 = l0^l2, q3 = l0^l3 (the flip of all four links maps to X on q0)
_CORNERS = (4, 5, 6, 7)
_A, _B, _C = 8, 9, 10                      # the three ancillas, in the sibling's order ANC[0..2]


def _nor4_flag(a: int, f: int) -> list:
    """F = NOR(c0..c3) into f: a = ~c0 ~c1 ~c2 (rc3x), f = a ~c3 (rccx)."""
    return [("x", q) for q in _CORNERS] + [("rc3x", 4, 5, 6, a), ("rccx", a, 7, f)]


def _p_flag(p: int) -> list:
    """P = ~q2 ~q3 into p."""
    return [("x", 2), ("x", 3), ("rccx", 2, 3, p)]


def _flags4() -> list:
    a, f, p = _A, _B, _C
    compute = _nor4_flag(a, f) + _p_flag(p)
    walk = [("rz", TARGET),
            ("rccx", p, 1, TARGET), ("rz", TARGET),
            ("rccx", f, p, TARGET), ("rz", TARGET),
            ("cx", f, TARGET), ("rz", TARGET),
            ("cx", f, TARGET), ("rccx", f, p, TARGET), ("rccx", p, 1, TARGET)]
    return compute + walk + mirror(compute)


def _flags5() -> list:
    a, f, p = _A, _B, _C
    compute = _nor4_flag(a, f) + _p_flag(p)
    walk = [("rz", TARGET),
            ("cx", f, TARGET), ("rz", TARGET), ("cx", f, TARGET),
            ("rccx", f, p, TARGET), ("rz", TARGET),
            ("cx", 1, TARGET), ("rz", TARGET), ("cx", 1, TARGET),
            ("rccx", f, p, TARGET),
            ("cx", 1, TARGET), ("rz", TARGET), ("cx", 1, TARGET)]
    return compute + walk + mirror(compute)


def _flags6() -> list:
    a, f, p = _A, _B, _C
    compute = _nor4_flag(a, f) + _p_flag(p)
    walk = [("rz", TARGET),
            ("cx", 1, TARGET), ("rz", TARGET),
            ("cx", p, TARGET), ("rz", TARGET),
            ("cx", 1, TARGET), ("rz", TARGET),
            ("cx", f, TARGET), ("rz", TARGET),
            ("cx", p, TARGET), ("rz", TARGET),
            ("cx", f, TARGET)]
    return compute + walk + mirror(compute)


def _closed_walk(order, wires) -> list:
    """One rz at each mask of `order` (tuples of wire labels; () = TARGET alone), consecutive masks joined by CX toggles
    from `wires[label]`, closed back to ()."""
    steps, cur = [], frozenset()
    for mask in order:
        new = frozenset(mask)
        steps += [("cx", wires[w], TARGET) for w in sorted(cur ^ new)]
        steps.append(("rz", TARGET))
        cur = new
    return steps + [("cx", wires[w], TARGET) for w in sorted(cur)]


def _pairs9() -> list:
    a, b, p = _A, _B, _C
    compute = [("x", q) for q in _CORNERS + (1, 2)] + [("rccx", 4, 6, a), ("rccx", 5, 7, b), ("rccx", 1, 2, p)]
    order = [(), ("b",), ("b", "P"), ("a", "b", "P"), ("a", "b"), ("a",), ("m3", "a"), ("m3", "a", "P"), ("P",)]
    return compute + _closed_walk(order, {"a": a, "b": b, "P": p, "m3": 3}) + mirror(compute)


# name -> (steps, number of ancillas, frame)
SKELETONS: dict = {
    "pairs9": (_pairs9(), 3, FRAME_B),
    "flags4": (_flags4(), 3, FRAME),
    "flags5": (_flags5(), 3, FRAME),
    "flags6": (_flags6(), 3, FRAME),
}
