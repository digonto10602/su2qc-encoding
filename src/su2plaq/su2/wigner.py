"""Wigner 6j symbols and the recoupling F-symbol (prompts/002 §2.2, docs/METHODS.md §5).

6j by Racah's closed formula (Edmonds, Angular Momentum in Quantum Mechanics, Eq. 6.3.7), cached on
doubled-integer arguments; the algorithm follows scratch/planner/proto_m0.py. No sympy in the package.
"""
from __future__ import annotations

import math
from functools import lru_cache


def _twice(x: float) -> int:
    return int(round(2 * x))


def triangle(a, b, c) -> bool:
    """True iff (a, b, c) satisfy |a-b| <= c <= a+b and a+b+c is an integer."""
    a2, b2, c2 = _twice(a), _twice(b), _twice(c)
    return abs(a2 - b2) <= c2 <= a2 + b2 and (a2 + b2 + c2) % 2 == 0


@lru_cache(maxsize=None)
def _six_j_2x(a2: int, b2: int, c2: int, d2: int, e2: int, f2: int) -> float:
    if min(a2, b2, c2, d2, e2, f2) < 0:
        return 0.0
    # the four triads (a b c), (a e f), (d b f), (d e c)
    for x, y, z in ((a2, b2, c2), (a2, e2, f2), (d2, b2, f2), (d2, e2, c2)):
        if not (abs(x - y) <= z <= x + y and (x + y + z) % 2 == 0):
            return 0.0
    F = math.factorial

    def delta(x, y, z):  # Delta(xyz)^2 with doubled integers
        return (F((x + y - z) // 2) * F((x - y + z) // 2) * F((-x + y + z) // 2)) / F((x + y + z) // 2 + 1)

    pref = math.sqrt(delta(a2, b2, c2) * delta(a2, e2, f2) * delta(d2, b2, f2) * delta(d2, e2, c2))
    t1, t2, t3, t4 = (a2 + b2 + c2) // 2, (a2 + e2 + f2) // 2, (d2 + b2 + f2) // 2, (d2 + e2 + c2) // 2
    q1, q2, q3 = (a2 + b2 + d2 + e2) // 2, (a2 + c2 + d2 + f2) // 2, (b2 + c2 + e2 + f2) // 2
    s = 0.0
    for z in range(max(t1, t2, t3, t4), min(q1, q2, q3) + 1):
        s += (-1) ** z * F(z + 1) / (F(z - t1) * F(z - t2) * F(z - t3) * F(z - t4) * F(q1 - z) * F(q2 - z) * F(q3 - z))
    return pref * s


def six_j(a, b, c, d, e, f) -> float:
    """Wigner 6j symbol {a b c; d e f}; 0.0 for inadmissible arguments."""
    return _six_j_2x(*(_twice(x) for x in (a, b, c, d, e, f)))


def f_symbol(j1, j2, j12, j3, J, j23) -> float:
    """<(j1 j2) j12, j3; J | j1, (j2 j3) j23; J> = (-1)^{j1+j2+j3+J} sqrt((2 j12+1)(2 j23+1)) {j1 j2 j12; j3 J j23}
    (Edmonds Eq. 6.1.5; Varshalovich-Moskalev-Khersonskii 8.1)."""
    phase = -1.0 if (_twice(j1) + _twice(j2) + _twice(j3) + _twice(J)) // 2 % 2 else 1.0
    return phase * math.sqrt((2 * j12 + 1) * (2 * j23 + 1)) * six_j(j1, j2, j12, j3, J, j23)
