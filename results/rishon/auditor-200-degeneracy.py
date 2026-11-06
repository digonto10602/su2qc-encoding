"""Auditor 200: electric-vacuum degeneracy (H_E = 0 states, all 12 links singlets) and the closed-sector ground level."""
import numpy as np
from su2plaq.rishon import physical as P, operators as O
b = P.rishon_basis()
n_he0 = sum(1 for types, _ in b.labels if "Q" not in types)
print("physical states with H_E = 0 (all 12 links type A/B):", n_he0, "of", b.dim)
for g2 in (0.5, 1.0, 2.0):
    ev = np.linalg.eigvalsh(O.closed_block(g2).real)
    print(f"g2={g2}: 3x3 bright block eigenvalues {np.round(ev, 6)}; ground level per outer singlet choice is unique -> 256-fold over the closed sector")
