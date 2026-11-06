"""Tester 201: per-corner kernel dimension: production eigh kernels vs production fusion table vs own 8-qubit brute force."""
import sys, itertools, json, importlib.util
import numpy as np
sys.path.insert(0, "src")
from su2plaq.rishon import physical as P
spec = importlib.util.spec_from_file_location("ind", "results/rishon/tester-201-independent-counts.py")
ind = importlib.util.module_from_spec(spec); spec.loader.exec_module(ind)
G, n = ind.end_gens(8); Gt = [sum(G[a][e] for e in range(4)) for a in range(3)]; C = sum(g @ g for g in Gt)
occ = np.stack([np.rint(np.diag(n[e]).real).astype(int) for e in range(4)], axis=1)
def own_dim(nt):
    sel = np.flatnonzero(np.all(occ == np.array(nt), axis=1)); return int((np.linalg.eigvalsh(C[np.ix_(sel, sel)]) < 1e-9).sum())
n_tab, q_tab = P._fusion_tables(); D = P._diagram()
mism_fus = mism_own = 0; ncase = 0
for c in range(4):
    ends = D.corners[c].ends
    for i, types4 in enumerate(P._all_types4(c)):
        kd = P._corner_kernel_cached(tuple((t, r) for t, (_, r) in zip(types4, ends)))[1].shape[1]
        mism_fus += int(kd != n_tab[c][i])
        # occupation of each end: from type & role (own rule: A = both rishons at L end; B = at R end; Q = one each)
        nt = []
        for t, (_, r) in zip(types4, ends):
            nt.append(1 if t == "Q" else (2 if (t == "A") == (r == "out") else 0))
        mism_own += int(kd != own_dim(tuple(nt))); ncase += 1
print(json.dumps({"corner_type_cases": ncase, "kernel_vs_fusion_mismatches": mism_fus, "kernel_vs_own_bruteforce_mismatches": mism_own}))
json.dump({"corner_type_cases": ncase, "kernel_vs_fusion_mismatches": mism_fus, "kernel_vs_own_bruteforce_mismatches": mism_own}, open("results/rishon/tester-201-corner-tables.json", "w"))
