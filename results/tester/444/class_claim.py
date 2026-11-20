"""Tester 444: own check of the structural claim behind the search (every walk must visit all 16 classes of F2^6 / <e, p+y1+y2+y3+a>).
Own labels/g from labels_own.json.  (1) H = {L : e=0, p+y1+y2+y3+a=0} has 16 elements, all realised labels, g = -4 at 0 and 0 on the other 15;
(2) annihilator H^perp = {0, 16, 47, 63} and the 16 classes (cosets) of 4 points each; (3) DIRECT linear-algebra test: for each class C, g is NOT in span{chi_x: x not in C} on the 37 labels
(rank test with exact rational arithmetic via sympy); (4) g IS in the span of chi_x over the whole 64-point space; (5) the Q5 projection maps classes to antipodal Q5 pairs.  No RNG."""
import json, itertools
import numpy as np, sympy
o = json.load(open("/home/digimonk/Projects/su2qc-encoding/results/tester/444/labels_own.json"))
g = {int(k): int(round(v)) for k, v in o["my_g"].items()}; LABS = sorted(g)
par = lambda x: bin(x).count("1") & 1
H = [L for L in range(64) if (L >> 4 & 1) == 0 and par(L & 47) == 0]
out = {"H": H, "H_all_realised": all(L in g for L in H), "g_on_H": {L: g[L] for L in H if g[L] != 0}, "g_on_H_nonzero_only_at_0_value": g[0]}
perp = [x for x in range(64) if all(par(x & L) == 0 for L in H)]
out["H_perp"] = perp
cls = {}
for x in range(64): cls.setdefault(min(x ^ s for s in perp), []).append(x)
out["n_classes"] = len(cls); out["class_sizes"] = sorted({len(v) for v in cls.values()})
chi = lambda x: [(-1) ** par(x & L) for L in LABS]
gv = sympy.Matrix([g[L] for L in LABS])
def in_span(xs):
    A = sympy.Matrix([chi(x) for x in xs]).T
    return A.rank() == A.row_join(gv).rank()
out["g_in_span_all_64"] = in_span(list(range(64)))
out["drop_class_infeasible"] = {}
for c, xs in sorted(cls.items()):
    rest = [x for x in range(64) if x not in xs]
    out["drop_class_infeasible"][c] = (not in_span(rest))
out["all_16_classes_necessary"] = all(out["drop_class_infeasible"].values())
q5class = lambda v: (v & 15) ^ (15 if (v >> 4) & 1 else 0)
pt = lambda v, e: (v & 15) | (e << 4) | (((v >> 4) & 1) << 5)
out["q5_class_map_consistent"] = all(sorted({min(pt(v, e) ^ s for s in perp) for e in (0, 1)}) == sorted({min(pt(v, e) ^ s for s in perp) for e in (0, 1)}) and len({min(pt(v, e) ^ s for s in perp) for e in (0, 1)}) == 1 for v in range(32))
out["q5_class_map_matches_cosets"] = all(q5class(v) == q5class(w) for v in range(32) for w in range(32) if min(pt(v, 0) ^ s for s in perp) == min(pt(w, 0) ^ s for s in perp)) and len({q5class(v) for v in range(32)}) == 16 and all((q5class(v) == q5class(w)) == (min(pt(v, 0) ^ s for s in perp) == min(pt(w, 0) ^ s for s in perp)) for v in range(32) for w in range(32))
print(json.dumps({k: v for k, v in out.items() if k != "drop_class_infeasible"}, indent=1)); print("drop-class infeasible:", out["drop_class_infeasible"])
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/444/class_claim.json", "w"), indent=1, default=str)
