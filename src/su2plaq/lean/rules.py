"""Polish rewrite rule -> Lean theorem (prompts/006 §5, docs/METHODS.md §11.4).

Every rule name that `compress.passes.polish` can emit in its log is a key; the value is the kernel-checked theorem
(standard axioms only) in `lean/Su2Plaq/Rewrites.lean` that proves the rewrite sound:

* `cancel_inverse_pairs`     -- each gate pair the pass cancels multiplies to the identity (x x, z z, h h, s sdg, sdg s,
  t tdg, tdg t, cx cx, cz cz, swap swap, ccx ccx, ccz ccz, ch ch, rccx rccx);
* `merge_adjacent_rotations` -- adjacent rz / p / rx (and controlled crz / cp / crx) rotations on the same qubits add their
  angles.
"""
from __future__ import annotations

LEAN_RULES: dict[str, str] = {
    "cancel_inverse_pairs": "Su2Plaq.cancel_inverse_pairs",
    "merge_adjacent_rotations": "Su2Plaq.merge_adjacent_rotations",
}
