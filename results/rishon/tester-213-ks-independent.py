"""Tester 213: independent recomputation of the rishon -> Kogut-Susskind one-singlet projection numbers.

Does NOT import scripts/m5_ks_projection.py.  Uses only: rishon_basis() (the 38 432 physical vectors: labels, 48-bit keys, amps),
physical_basis() (KS labels) and spinnet.h_magnetic_phys_6j (KS H_B, route B).  Everything else (rishon link operators from a
bit-level Jordan-Wigner, inner H_B, projection vectors, gauge fit, reductions, expm, leakage by explicit residual) is coded here.

    PYTHONPATH=src taskset -c 10-19 python results/rishon/tester-213-ks-independent.py [out.json]
"""
import json, sys, time, resource, subprocess
import numpy as np, scipy.linalg as sla, scipy.sparse as sp

t0 = time.time()
ALPHA, BETA = 0.37, 0.61
BETAS = (0.61, 0.3, 0.1, 0.03)
A_, B_, QS = 3, 12, (5, 6, 9, 10)
SECTOR = [3, 5, 6, 9, 10, 12]
POS = {c: i for i, c in enumerate(SECTOR)}

# ------------------------------------------------ rishon link operators (bit-level JW, 4 modes: L1 L2 R1 R2 = bits 0..3)
def cop(k, dag=False):
    M = np.zeros((16, 16))
    for n in range(16):
        occ = (n >> k) & 1
        if (occ == 1 and not dag) or (occ == 0 and dag):
            sign = -1.0 if bin(n & ((1 << k) - 1)).count("1") % 2 else 1.0
            M[n ^ (1 << k), n] = sign
    return M

def sec(M):
    return M[np.ix_(SECTOR, SECTOR)]

U = [[sec(cop(i) @ cop(2 + j, True)) for j in range(2)] for i in range(2)]      # U_ij = c_{L,i} c^dag_{R,j}
Ud = [[U[i][j].T.copy() for j in range(2)] for i in range(2)]                    # (U_ij)^dagger (real matrices)
# check the sector is preserved by U_ij (leak outside the 6-state sector)
for i in range(2):
    for j in range(2):
        full = cop(i) @ cop(2 + j, True)
        out = np.delete(np.arange(16), SECTOR)
        assert np.abs(full[np.ix_(out, SECTOR)]).max() < 1e-14

def kron4(f):   # f[l] = 6x6 of link l, link 0 least significant
    out = np.ones((1, 1))
    for l in range(4):
        out = np.kron(f[l], out)
    return out

import itertools
W = np.zeros((1296, 1296))
for a, b, c, d in itertools.product(range(2), repeat=4):
    W += kron4([U[a][b], U[b][c], Ud[d][c], Ud[a][d]])      # links (b, r, t, l):  Tr(U_b U_r U_t^+ U_l^+)
HB_R = -(W + W.T)                                             # inner rishon H_B (1296 x 1296, real symmetric)
nQ_in = np.zeros(1296)
for idx, cfg in enumerate(itertools.product(range(6), repeat=4)):   # cfg = (d3,d2,d1,d0)
    nQ_in[idx] = sum(1 for d in cfg if SECTOR[d] in QS)
HE_R = 0.75 * nQ_in                                           # 3/4 per quartet inner link (diag)

# ------------------------------------------------ bases
sys.path.insert(0, "src")
from su2plaq.rishon.physical import rishon_basis
from su2plaq.exact.physical import physical_basis
from su2plaq.exact import spinnet

b = rishon_basis(); ksb = physical_basis(); labs = ksb.labels
HK = spinnet.h_magnetic_phys_6j(labs)
HEK = np.array([sum(x * (x + 1) for x in j[:4]) for j, _ in labs])   # KS inner H_E (diagonal)
kidx = {(tuple(float(x) for x in j), tuple(float(x) for x in J)): i for i, (j, J) in enumerate(labs)}
N = len(b.labels); assert N == 38432 and len(labs) == 433

typ = lambda lab: lab[0]
grp = np.zeros(N, dtype=np.int64); n0 = np.zeros(N, dtype=np.int64)
for k, (types, Js) in enumerate(b.labels):
    grp[k] = kidx[(tuple(0.5 if t == "Q" else 0.0 for t in types), tuple(float(x) for x in Js))]
    n0[k] = sum(1 for t in types if t != "Q")
sizes = np.bincount(grp, minlength=433)
res = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
       "group_sizes_are_2^n0": bool(all(sizes[g] == 2 ** n0[grp == g][0] and (n0[grp == g] == n0[grp == g][0]).all() for g in range(433))),
       "n_groups": int((sizes > 0).sum()), "sum_sizes": int(sizes.sum())}

# ---- closure identity: flipping A<->B in the nibble of a spin-0 link maps a basis vector exactly onto the basis vector of the flipped label
KEYMAP = [dict(zip(map(int, b.keys[k]), np.asarray(b.amps[k]).tolist())) for k in range(0)]  # not used (memory)
lab_index = {lab: i for i, lab in enumerate(b.labels)}
worst = 0.0; nchecks = 0
for k, (types, Js) in enumerate(b.labels):
    for l, t in enumerate(types):
        if t == "Q":
            continue
        flip = list(types); flip[l] = "B" if t == "A" else "A"
        k2 = lab_index[(tuple(flip), Js)]
        key1 = np.asarray(b.keys[k], dtype=np.int64) ^ (np.int64(15) << (4 * l))
        key2 = np.asarray(b.keys[k2], dtype=np.int64)
        o1, o2 = np.argsort(key1), np.argsort(key2)
        if not np.array_equal(key1[o1], key2[o2]):
            worst = max(worst, 1e9)
        else:
            worst = max(worst, float(np.abs(np.asarray(b.amps[k])[o1] - np.asarray(b.amps[k2])[o2]).max()))
        nchecks += 1
res["closure_identity_checks"] = nchecks
res["closure_identity_max_amp_diff"] = worst
print(f"[{time.time()-t0:6.1f}s] closure identity: {nchecks} flips, worst diff {worst}", flush=True)

# ------------------------------------------------ V columns, reductions
def make_V(variant):
    s = {"plus": 1.0, "minus": -1.0, "A": None}[variant]
    w = np.ones(N)
    for k, (types, Js) in enumerate(b.labels):
        for t in types:
            if t == "Q":
                continue
            if s is None:
                w[k] *= 1.0 if t == "A" else 0.0
            else:
                w[k] *= (1.0 if t == "A" else s) / np.sqrt(2.0)
    nrm = np.zeros(433)
    np.add.at(nrm, grp, w ** 2)
    w = w / np.sqrt(nrm[grp])
    return w

# precompute for all states: (outer key, inner index, state k, ...) as flat arrays
lens = np.array([len(x) for x in b.keys])
K = np.concatenate([np.asarray(x, dtype=np.int64) for x in b.keys])
AMP = np.concatenate([np.asarray(x, dtype=np.complex128) for x in b.amps])
STATE = np.repeat(np.arange(N), lens)
inner = K & 0xFFFF; outer = K >> 16
# inner code -> index via nibble digits
lut = np.full(16, -1); lut[SECTOR] = np.arange(6)
dig = np.stack([lut[(inner >> (4 * l)) & 15] for l in range(4)])
assert (dig >= 0).all(), "inner nibble outside the 2-rishon sector"
INNER_IDX = dig[3] * 216 + dig[2] * 36 + dig[1] * 6 + dig[0]
order = np.lexsort((INNER_IDX, outer)); K, AMP, STATE, outer, INNER_IDX = K[order], AMP[order], STATE[order], outer[order], INNER_IDX[order]
bounds = np.flatnonzero(np.concatenate(([True], outer[1:] != outer[:-1], [True])))
res["n_outer_patterns"] = int(len(bounds) - 1)
print(f"[{time.time()-t0:6.1f}s] flat arrays: nnz {len(K)}, outer patterns {len(bounds)-1}", flush=True)

def blocks(w):
    """Yield (rows, Z) per outer pattern: Z (len(rows) x len(cols)) dense, cols = KS columns touched."""
    for a, z in zip(bounds[:-1], bounds[1:]):
        st = STATE[a:z]; c = grp[st]; r = INNER_IDX[a:z]; amp = AMP[a:z] * w[st]
        keep = amp != 0
        if not keep.any():
            continue
        c, r, amp = c[keep], r[keep], amp[keep]
        cs, ci = np.unique(c, return_inverse=True); rs, ri = np.unique(r, return_inverse=True)
        Z = np.zeros((len(rs), len(cs)), dtype=np.complex128)
        np.add.at(Z, (ri, ci), amp)
        yield rs, cs, Z

def reduce(w, ops):
    out = [np.zeros((433, 433), dtype=np.complex128) for _ in ops]
    for rs, cs, Z in blocks(w):
        ix = np.ix_(cs, cs)
        for k, O in enumerate(ops):
            out[k][ix] += Z.conj().T @ (O[np.ix_(rs, rs)] @ Z)
    return out

def residual_gram(w, C):
    """R^dag R with R = (C (x) 1) V - V W  (W = V^dag C V given),  assembled block by block without forming R:
    per outer pattern  R_o = E X - S Y,  X = C[:, rs] Z (1296 x |cs|),  Y = Z Wm[cs, :] (|rs| x 433), E embeds the columns cs, S the rows rs."""
    C, Wm = C
    G = np.zeros((433, 433), dtype=np.complex128)
    for rs, cs, Z in blocks(w):
        X = C[:, rs] @ Z
        Y = Z @ Wm[cs, :]
        Xr = X[rs, :]
        G[np.ix_(cs, cs)] += X.conj().T @ X
        T = Xr.conj().T @ Y
        G[cs, :] -= T
        G[:, cs] -= T.conj().T
        G += Y.conj().T @ Y
    return G

def sparse_gauge_fit(HR, HKs, c):
    """D real +-1 with HR = D (c HK) D by BFS sign propagation on the KS graph; returns (D, residual, n_components, ratio_realness)."""
    n = len(HR); D = np.zeros(n); ncomp = 0
    nz = np.abs(HKs) > 1e-9
    maxratio_imag = 0.0
    for r in range(n):
        if D[r] != 0:
            continue
        ncomp += 1; D[r] = 1.0; stack = [r]
        while stack:
            i = stack.pop()
            for j in np.flatnonzero(nz[i]):
                if D[j] == 0:
                    ratio = HR[i, j] / (c * HKs[i, j])
                    maxratio_imag = max(maxratio_imag, abs(ratio.imag))
                    D[j] = D[i] * np.sign(ratio.real); stack.append(j)
    resid = np.abs(HR - c * D[:, None] * HKs * D[None, :]).max()
    return D, float(resid), ncomp, maxratio_imag

def opn(A): return float(np.linalg.norm(A, 2))

def unitary_dense(beta, alpha):
    return sla.expm(-1j * beta * HB_R) @ np.diag(np.exp(-1j * alpha * HE_R))

out = {}
Hsym = float(np.abs(HB_R - HB_R.T).max())
ev = np.linalg.eigvalsh(HB_R)
out["rishon_inner_HB"] = {"hermitian_resid": Hsym, "top_eig": float(ev[-1]), "bottom_eig": float(ev[0]), "4sqrt2": 4 * np.sqrt(2)}
# cross-check my inner H_B/H_E against the library's (shared formula but independent coding of the link operators)
from su2plaq.rishon import operators as rops
out["rishon_inner_HB"]["max_diff_vs_library_h_magnetic_inner"] = float(np.abs(HB_R - rops.h_magnetic_inner()).max())
out["rishon_inner_HB"]["max_diff_vs_library_h_electric_inner"] = float(np.abs(HE_R - rops.h_electric_inner()).max())
HB2_R = HB_R @ HB_R

# KS exact comparison unitaries (own construction)
def ks_unitary(beta, alpha, c=1.0):
    return sla.expm(-1j * beta * c * HK) @ np.diag(np.exp(-1j * alpha * HEK))
out["KS_HB_hermitian_resid"] = float(np.abs(HK - HK.T).max()); out["KS_HB_norm"] = opn(HK)

ctrl = {}
for variant in ("plus", "minus", "A"):
    w = make_V(variant)
    ops = [HB_R, HB2_R, np.diag(HE_R)] + [unitary_dense(bt, ALPHA) for bt in BETAS]
    red = reduce(w, ops)
    VV = reduce(w, [np.eye(1296)])[0]
    M, M2, HEp = red[0], red[1], red[2]
    Ws = dict(zip(BETAS, red[3:]))
    r = {"V_dagV_minus_1": float(np.abs(VV - np.eye(433)).max()),
         "trace_P_on_physical = sum_s <psi_s|P|psi_s> = sum 2^-n0": float(np.sum(2.0 ** (-n0.astype(float)))),
         "HE": {"max_offdiag": float(np.abs(HEp - np.diag(np.diag(HEp))).max()), "diag_minus_KS": float(np.abs(np.diag(HEp).real - HEK).max())},
         "HB_hermitian": float(np.abs(M - M.conj().T).max())}
    # c (modulus least-squares), gauge
    aR, aK = np.abs(M), np.abs(HK)
    c = float((aR * aK).sum() / (aK * aK).sum())
    r["c_modulus_lsq"] = c; r["modulus_residual"] = float(np.abs(aR - c * aK).max())
    r["support_equal"] = bool(((aR > 1e-9) == (aK > 1e-9)).all())
    if c > 1e-9:
        D, gres, ncomp, imag = sparse_gauge_fit(M, HK, c)
        r["gauge"] = {"residual_HR_minus_c_D_HK_D": gres, "n_KS_graph_components": ncomp, "max_imag_of_entry_ratio": imag}
    else:
        D = None
    r["norm_P_HB_P"] = opn(M)
    lam = np.linalg.eigvalsh((M2 - M @ M + (M2 - M @ M).conj().T) / 2)
    r["leak_HB_gram_sqrt_lmax"] = float(np.sqrt(max(lam.max(), 0)))
    r["leak_HB_lmax"] = float(lam.max()); r["leak_HB_lmin"] = float(lam.min())
    # explicit residual route
    if variant == "plus":
        G = residual_gram(w, (HB_R.astype(np.complex128), M))
        r["leak_HB_explicit_residual_norm"] = float(np.sqrt(np.linalg.eigvalsh((G + G.conj().T) / 2).max()))
    # nominal / small beta
    rows = []
    for bt in BETAS:
        Wm = Ws[bt]
        sv = np.linalg.svd(Wm, compute_uv=False)
        leak_gram = float(np.sqrt(max(np.linalg.eigvalsh(np.eye(433) - Wm.conj().T @ Wm).max(), 0)))
        row = {"beta": bt, "leak_from_W": leak_gram, "sv_min": float(sv.min())}
        if variant == 'plus' and bt in (0.61, 0.03):
            C = unitary_dense(bt, ALPHA)
            Gr = residual_gram(w, (C, Wm))
            row["leak_explicit_residual"] = float(np.sqrt(max(np.linalg.eigvalsh((Gr + Gr.conj().T) / 2).max(), 0)))
        if c > 1e-9:
            Uk = ks_unitary(bt, ALPHA, c)
            if D is not None:
                Ukd = D[:, None] * Uk * D[None, :]
                row["mismatch_op_gauged"] = opn(Wm - Ukd)
                row["mismatch_op_ungauged"] = opn(Wm - Uk)
                row["mismatch_over_beta2"] = row["mismatch_op_gauged"] / bt ** 2
                row["leak_over_beta"] = leak_gram / bt
                row["predicted_half_leakHB2_beta2"] = 0.5 * r["leak_HB_gram_sqrt_lmax"] ** 2 * bt ** 2
        rows.append(row)
    r["steps"] = rows
    # slopes
    r["slopes_log_log"] = {"leak": [float(np.log(rows[i + 1]["leak_from_W"] / rows[i]["leak_from_W"]) / np.log(rows[i + 1]["beta"] / rows[i]["beta"])) for i in range(3)]}
    if "mismatch_op_gauged" in rows[0]:
        r["slopes_log_log"]["mismatch"] = [float(np.log(rows[i + 1]["mismatch_op_gauged"] / rows[i]["mismatch_op_gauged"]) / np.log(rows[i + 1]["beta"] / rows[i]["beta"])) for i in range(3)]
    ctrl[variant] = r
    print(f"[{time.time()-t0:6.1f}s] variant {variant} done: c={c:.12g}", flush=True)
    if variant == "plus":
        # Gauss residual of the V columns (shared library helper) -- sample of columns
        pass
out["variants"] = ctrl

# ------------------------------------------------ closed pair argument (inner-level, P_in = prod over 4 inner links)
w_, v_ = np.linalg.eigh(HB_R)
top = v_[:, -1]; bot = v_[:, 0]
Qt = (top + bot) / np.sqrt(2); phi = (top - bot) / np.sqrt(2)
Pin = np.ones((1, 1))
Pl = np.zeros((6, 6))
for q in QS:
    Pl[POS[q], POS[q]] = 1
s_vec = np.zeros(6); s_vec[POS[A_]] = s_vec[POS[B_]] = 1 / np.sqrt(2)
Pl_plus = Pl + np.outer(s_vec, s_vec)
Pin = kron4([Pl_plus] * 4)
nonQ_weight_of_top = float(np.sum(np.abs(Qt) ** 2 * (nQ_in == 4)))
out["closed_pair"] = {
    "eig_top": float(w_[-1]), "eig_bottom": float(w_[0]), "n_eig_equal_top": int(np.sum(np.abs(w_ - w_[-1]) < 1e-9)),
    "weight_of_Qtilde_on_all-Q-inner_codes": nonQ_weight_of_top,
    "||H Qtilde||^2": float(np.linalg.norm(HB_R @ Qt) ** 2), "||P H Qtilde||^2 (inner P)": float(np.linalg.norm(Pin @ HB_R @ Qt) ** 2),
    "||(1-P)H Qtilde||^2": float(np.linalg.norm((np.eye(1296) - Pin) @ HB_R @ Qt) ** 2),
    "Qtilde_is_P_fixed": float(np.linalg.norm(Pin @ Qt - Qt)),
    "|<sigma-vec|phi>|^2 = ||P phi||^2": float(np.linalg.norm(Pin @ phi) ** 2),
    "KS_top_eig": float(np.linalg.eigvalsh(HK)[-1]),
}
th = 4 * np.sqrt(2) * BETA
out["closed_pair"]["rishon_closed_angle_4sqrt2_beta"] = th
out["closed_pair"]["KS_closed_angle_2beta"] = 2 * BETA
out["closed_pair"]["leak_of_Qtilde_after_UB_numeric"] = float(np.linalg.norm((np.eye(1296) - Pin) @ sla.expm(-1j * BETA * HB_R) @ Qt))
out["closed_pair"]["leak_of_Qtilde_after_UB_formula_sin(theta)*sqrt(1-|P phi|^2)"] = float(abs(np.sin(th)) * np.sqrt(1 - np.linalg.norm(Pin @ phi) ** 2))

res["results"] = out
res["wall_seconds"] = time.time() - t0
res["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
res["seed"] = "none (deterministic)"
path = sys.argv[1] if len(sys.argv) > 1 else "results/rishon/tester-213-ks-independent.json"
json.dump(res, open(path, "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
print("wrote", path, f"wall {res['wall_seconds']:.0f}s rss {res['peak_rss_mb']:.0f}MB")
