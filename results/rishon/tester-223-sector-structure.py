"""Tester 223 (rishon D4): det_sector_structure recomputed with my own operators and a residual-based leaving weight.
Own JW link algebra (as tester-222-det-independent.py) -> own H_B (1296 inner codes); det term of a link = nibble flip A(3)<->B(12) with
amplitude 2 derived from my own det U matrix (not typed); blocks = connected components of P^dag H P thresholded; leaving weight computed
as ||(1 - P G^-1 P^dag) H P||_F^2 from the residual itself (no difference of two O(1e6) sums).  Production imported only for the basis
(states, amplitudes, U(1) charges) and for the comparison.  Run: PYTHONPATH=src python this.  Output: results/rishon/tester-223-sector-structure.json"""
import itertools, json, subprocess, sys, time
import numpy as np, scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
t0 = time.time()
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1:
            M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
U = lambda i, j: c[i] @ cd[2 + j]
res = lambda M: M[np.ix_(SECTOR, SECTOR)]
Ub = [[res(U(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Ub[i][j].T for j in range(2)] for i in range(2)]
detU = U(0, 0) @ U(1, 1) - U(0, 1) @ U(1, 0)
nzr = np.argwhere(np.abs(detU) > 1e-14)
assert len(nzr) == 1 and abs(detU[tuple(nzr[0])] - 2) < 1e-14 and tuple(nzr[0]) == (12, 3)   # derived: |B><A| * 2
def kron4(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]]) for a, b, cc, d in itertools.product(range(2), repeat=4))
HB_own = sp.csr_matrix(-(W + W.T))                    # 1296 x 1296 in row-major sector index, link 0 least significant
codes_by_idx = np.array([sum(SECTOR[(i // 6 ** l) % 6] << (4 * l) for l in range(4)) for i in range(1296)], dtype=np.int64)
idx_of_code = {int(cc): i for i, cc in enumerate(codes_by_idx)}

from su2plaq.rishon import physical as phys
b = phys.rishon_basis()
n = int(b.dim)
lens = np.array([len(k) for k in b.keys])
allk = np.concatenate([np.asarray(k, dtype=np.int64) for k in b.keys]); alla = np.concatenate([np.asarray(a, dtype=np.complex128) for a in b.amps])
uk, row = np.unique(allk, return_inverse=True); nu = len(uk)
P = sp.csr_matrix((alla, (row, np.repeat(np.arange(n), lens))), shape=(nu, n))
G = (P.conj().T @ P).tocsr()
Gd = (G - sp.identity(n, format='csr')).tocsr()
rec = {"dim": n, "n_codes": int(nu), "gram_dev_from_identity": float(abs(Gd).max())}

# H_B on the 48-bit codes: inner 16 bits through my own matrix, outer bits spectators
inner = uk & 0xFFFF; outer = uk >> 16
HBc = HB_own.tocsc()
def tgt_code(col, j):
    return (int(outer[col]) << 16) | int(codes_by_idx[j])
allcodes = set(int(x) for x in uk)
trip = []
for i in range(nu):
    ii = idx_of_code[int(inner[i])]
    s, e = HBc.indptr[ii], HBc.indptr[ii + 1]
    for j, v in zip(HBc.indices[s:e], HBc.data[s:e]):
        t = tgt_code(i, j)
        allcodes.add(t); trip.append((t, i, v))
def det_triples(link):
    sh = 4 * link
    out = []
    for i, k in enumerate(uk):
        nib = (int(k) >> sh) & 15
        if nib in (3, 12):                       # the only column of my own det U with a non-zero entry is A (3) -> B (12); h.c. gives B -> A
            t = int(k) ^ (15 << sh)
            allcodes.add(t); out.append((t, i, 2.0))
    return out
dets = {l: det_triples(l) for l in range(12)}
big = np.array(sorted(allcodes), dtype=np.int64); bpos = {int(k): i for i, k in enumerate(big)}
N = len(big)
def mk(tr):
    r = np.array([bpos[t] for t, _, _ in tr]); cidx = np.array([ui for _, ui, _ in tr]); v = np.array([x for _, _, x in tr], dtype=float)
    cols = np.array([bpos[int(uk[x])] for x in cidx])
    return sp.csr_matrix((v, (r, cols)), shape=(N, N))
Pc = P.tocoo()
Pbig = sp.csr_matrix((Pc.data, (np.array([bpos[int(uk[i])] for i in Pc.row]), Pc.col)), shape=(N, n))
TB = mk(trip); TDl = {l: mk(dets[l]) for l in range(12)}
# dense n x n is too large; use the fact that P is (numerically) an isometry: R = X - P (P^dag X), with P^dag X sparse
def leaving_sparse(T):
    X = (T @ Pbig).tocsc()
    M = (Pbig.conj().T @ X).tocsc()
    Rm = (X - Pbig @ M).tocsc()
    Rm.data[np.abs(Rm.data) < 1e-300] = 0
    return float((np.abs(Rm.data) ** 2).sum()), float(np.abs(Rm.data).max()) if Rm.nnz else 0.0, M
wt = {}
Mp = {}
t = time.time()
wt["HB"], mx, Mp["HB"] = leaving_sparse(TB); rec["resid_maxabs_HB"] = mx
w_all = []
for l in range(12):
    w, mx, Mp[l] = leaving_sparse(TDl[l]); w_all.append((w, mx))
rec["leaving_weight_residual"] = {"HB": wt["HB"], "det_per_link": [w for w, _ in w_all], "det_max_abs_entry_of_residual": [m for _, m in w_all]}
Tin = sum(TDl[l] for l in range(4)); Tout = sum(TDl[l] for l in range(4, 12))
wi, mxi, Din = leaving_sparse(Tin); wo, mxo, Dout = leaving_sparse(Tout)
rec["leaving_weight_residual"].update({"det_inner_sum": wi, "det_outer_sum": wo})
rec["leaving_weight_residual_max"] = float(max([wt["HB"], wi, wo] + [w for w, _ in w_all]))
rec["t_leaving_s"] = time.time() - t

def thr(Mx, tol=1e-12):
    Mx = Mx.tocoo(); keep = np.abs(Mx.data) > tol
    return sp.csr_matrix((np.ones(int(keep.sum()), dtype=np.int8), (Mx.row[keep], Mx.col[keep])), shape=(n, n))
res_blocks = {}
for tol in (1e-9, 1e-12, 1e-14):
    nb = {}
    for name, Mx in (("lam0", Mp["HB"]), ("inner_det", Mp["HB"] + Din), ("full_det", Mp["HB"] + Din + Dout)):
        k, lab = connected_components(thr(Mx, tol), directed=False)
        sizes = np.bincount(lab)
        nb[name] = {"blocks": int(k), "max_block": int(sizes.max()), "size_histogram_top": {str(s): int(cnt) for s, cnt in zip(*np.unique(sizes, return_counts=True))}}
    res_blocks[str(tol)] = nb
rec["blocks_by_threshold"] = res_blocks
# reference block
k0 = phys.closed_indices(b)[0]
refs = {}
ch = np.array([b.u1_charges(k) for k in range(n)], dtype=np.int64)
for name, Mx in (("lam0", Mp["HB"]), ("inner_det", Mp["HB"] + Din), ("full_det", Mp["HB"] + Din + Dout)):
    k, lab = connected_components(thr(Mx, 1e-12), directed=False)
    mask = lab == lab[k0]
    refs[name] = {"dim": int(mask.sum()), "u1_sectors": len({tuple(x) for x in ch[mask]})}
rec["ref_block"] = refs
rec["n_u1_sectors"] = len({tuple(x) for x in ch})
def dq(Mx):
    co = thr(Mx).tocoo(); return sorted({tuple(int(y) for y in x) for x in (ch[co.row] - ch[co.col])})
dqs = {"HB": dq(Mp["HB"]), "in": dq(Din), "out": dq(Dout)}
rec["charge_changes"] = {k: [list(x) for x in v] for k, v in dqs.items()}
rank = lambda ms: int(np.linalg.matrix_rank(np.array(sorted(set().union(*[set(m) for m in ms]))))) if any(len(m) for m in ms) else 0
rec["charge_rank_own"] = {"lam0": rank([dqs["HB"]]), "inner_det": rank([dqs["HB"], dqs["in"]]), "full_det": rank([dqs["HB"], dqs["in"], dqs["out"]])}
# commutations (exact factorisation claim): outer det row commutes with H_B and the inner det terms on the physical space
def comm(A, B_): C = (A @ B_ - B_ @ A).tocsr(); return float(abs(C).max()) if C.nnz else 0.0
rec["comm_out_HB"] = comm(Dout, Mp["HB"]); rec["comm_out_in"] = comm(Dout, Din); rec["comm_in_HB"] = comm(Din, Mp["HB"])
# production
t = time.time()
prod = phys.det_sector_structure(b)
rec["production"] = prod; rec["t_production_s"] = time.time() - t
rec["agree"] = {k: prod[k] == v for k, v in (("blocks", {nm: res_blocks["1e-12"][nm]["blocks"] for nm in res_blocks["1e-12"]}),
        ("max_block", {nm: res_blocks["1e-12"][nm]["max_block"] for nm in res_blocks["1e-12"]}),
        ("ref_block_dim", {nm: refs[nm]["dim"] for nm in refs}), ("ref_block_u1_sectors", {nm: refs[nm]["u1_sectors"] for nm in refs}),
        ("charge_change_rank", rec["charge_rank_own"]), ("u1_sectors", rec["n_u1_sectors"]), ("dim", n))}
rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
rec["t_total_s"] = time.time() - t0
json.dump(rec, open("results/rishon/tester-223-sector-structure.json", "w"), indent=1, default=str)
print(json.dumps({k: rec[k] for k in ("leaving_weight_residual_max", "ref_block", "charge_rank_own", "agree", "comm_out_HB", "comm_out_in", "comm_in_HB")}, indent=1, default=str))
print("production leaving_weight", prod["leaving_weight"], "t", rec["t_total_s"])
