"""Tester 409: the residual form ||(1-PP^dag)TP||_F^2 of det_sector_structure.leaving_weight is O(dim) for an operator that leaves the physical space
(a single bit flip on qubit 0 and a single-link 'half' det, one nibble 3->5 flip) and ~0 for the true det term.  Own re-implementation of the P matrix from rishon_basis()."""
import json, numpy as np, scipy.sparse as sp
from su2plaq.rishon import physical as phys
b = phys.rishon_basis(); n = int(b.dim)
lens = np.array([len(k) for k in b.keys]); allk = np.concatenate([np.asarray(k, dtype=np.int64) for k in b.keys]); alla = np.concatenate([np.asarray(a, dtype=np.complex128) for a in b.amps])
uk, row = np.unique(allk, return_inverse=True); nu = len(uk)
P = sp.csr_matrix((alla, (row, np.repeat(np.arange(n), lens))), shape=(nu, n))
def leak(shift_xor, nib_from=None):
    src = np.arange(nu); tgt = uk ^ shift_xor
    allc = np.unique(np.concatenate([uk, tgt])); pos = {int(k): i for i, k in enumerate(allc)}
    sel = np.ones(nu, bool) if nib_from is None else (((uk >> nib_from[0]) & 15) == nib_from[1])
    T = sp.csr_matrix((np.ones(sel.sum()), (np.array([pos[int(t)] for t in tgt[sel]]), np.array([pos[int(uk[i])] for i in np.flatnonzero(sel)]))), shape=(len(allc), len(allc)))
    Pb = sp.csr_matrix((P.tocoo().data, (np.array([pos[int(uk[i])] for i in P.tocoo().row]), P.tocoo().col)), shape=(len(allc), n))
    X = (T @ Pb).tocsr(); M = (Pb.conj().T @ X).tocsr(); R = (X - Pb @ M).tocsr()
    return float(np.sum(np.abs(R.data) ** 2)), float(X.multiply(X.conj()).sum().real - M.multiply(M.conj()).sum().real)
out = {"dim": n, "flip_bit0_(residual, old_difference)": leak(1), "flip_nibble0_3_to_5_(only where nibble==3)": leak(3 ^ 5, (0, 3))}
print(out); json.dump(out, open("results/rishon/tester-409-leaving-sanity.json", "w"), indent=1)
