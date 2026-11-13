"""Tester 411: independent T-count of the det layer: 8 x rz(2 eta), eta=0.29, with pygridsynth directly (no su2plaq code)."""
import json, mpmath, pygridsynth
from pygridsynth.gridsynth import gridsynth_gates
res = {}
for eps in [1e-4, 1e-6, 1e-8, 1e-10]:
    theta = 2*0.29
    g = gridsynth_gates(mpmath.mpmathify(theta), mpmath.mpmathify(eps))
    s = g if isinstance(g, str) else str(g)
    t = s.count("T")
    res[str(eps)] = {"T_per_rotation": t, "x8": 8*t}
    print(eps, t, 8*t)
json.dump(res, open("results/rishon/tester-411-tcount-check.json","w"), indent=1)
