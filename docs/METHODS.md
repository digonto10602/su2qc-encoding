# METHODS — su2qc-encoding

Every numerical method in use: equations, conventions, source. The planner fills this in at kickoff.

## Conventions
- Spins $j \in \{0, \tfrac12, \dots, j_{\max}\}$, stored exactly as `fractions.Fraction` in counting code.
- Geometry and link names: `refs/su2_plaquette_truncations_encodings.md` §1 and `refs/su2_plaquette_encodings.py` docstring.

## Methods (stub)
1. **Intertwiner counting at a 4-valent corner** — number of singlets in $a\otimes b\otimes c\otimes d$
   is the number of intermediate spins $J$ with $(a,b,J)$ and $(c,d,J)$ both admissible
   (triangle rule, integer sum; SU(2)$_k$ adds $a+b+J\le k$).
   Checked numerically by counting zero eigenvalues of the total Casimir $\mathbf S^2$.
   Source: reference script `n_intertwiners`, `singlet_dim_numeric`; q-deformed rule from arXiv:2304.02527.
2. **Gauge-invariant state counts** — sum over inner-link spins of the product over corners of the
   intertwiner counts summed over that corner's outer spins. Source: reference script `count_states`.
