import json, sys, numpy as np, scipy.linalg as sl, scipy.sparse as sp
sys.path.insert(0, "src")
from su2plaq.encodings.spinnet import SpinNet, code_of_label, label_of_code, CORNER_LINKS
from su2plaq.exact.compare import gauge_align
from su2plaq.exact.operators import h_magnetic_phys, target as targetA
from su2plaq.exact.physical import gauss_residual
from su2plaq.su2.algebra import LinkSpace
out = {}
enc = SpinNet()
basis = enc.basis
inner = enc.inner_codes()
phys = set(enc._codes.tolist())
allc = [int(c) | (o << 8) for c in inner for o in range(256)]
bad = [c for c in allc if c not in phys]
out["n_codes"], out["n_bad"] = len(allc), len(bad)
# --- decode all codes into sparse matrix
cols, rows, vals = [], [], []
for i, c in enumerate(allc):
    k, v = enc.decode_state(np.array([c]), np.array([1.0+0j]))
    rows.append(k); cols.append(np.full(len(k), i)); vals.append(v)
rows = np.concatenate(rows); cols = np.concatenate(cols); vals = np.concatenate(vals)
uk, inv = np.unique(rows, return_inverse=True)
A = sp.csr_matrix((vals, (inv, cols)), shape=(len(uk), len(allc)))
G = (A.conj().T @ A).toarray()
out["gram_max_dev_from_identity_all12032"] = float(np.abs(G - np.eye(len(allc))).max())
physidx = [i for i, c in enumerate(allc) if c in phys]
badidx = [i for i, c in enumerate(allc) if c not in phys]
out["gram_phys_vs_bad_max"] = float(np.abs(G[np.ix_(physidx, badidx)]).max())
out["gram_bad_offdiag_max"] = float(np.abs(G[np.ix_(badidx, badidx)] - np.eye(len(badidx))).max())
# --- Gauss residual, library
from su2plaq.exact.physical import gauss_residuals_coo
ks, vs = [], []
for i in badidx:
    k, v = enc.decode_state(np.array([allc[i]]), np.array([1.0+0j])); ks.append(k); vs.append(v)
res_lib = gauss_residuals_coo(basis, ks, vs)
out["bad_gauss_min_lib"] = float(res_lib.min()); out["bad_gauss_max_lib"] = float(res_lib.max())
# --- independent Gauss residual (own implementation from LinkSpace generators)
ls = LinkSpace(0.5); L, R = ls.generators()
# check generator facts: L^z = -m_L, R^z = +m_R on the diag
for (j, mL, mR), k in ls.index.items():
    assert abs(L[2][k, k].real - (-mL)) < 1e-12 or j == 0, (j, mL, mR, L[2][k,k])
    assert abs(R[2][k, k].real - (mR)) < 1e-12 or j == 0
def apply(vec, link, M):
    o = {}
    for key, a in vec.items():
        s = (key // 5**link) % 5; base = key - s*5**link
        for sp_ in range(M.shape[0]):
            m = M[sp_, s]
            if abs(m) > 0:
                kk = base + sp_*5**link; o[kk] = o.get(kk, 0) + m*a
    return o
def own_resid(keys, amps):
    vec = dict(zip(keys.tolist(), amps.tolist())); worst = 0
    for corner in basis.diagram.corners:
        for a in range(3):
            tot = {}
            for link, role in corner.ends:
                r = apply(vec, link, L[a] if role == "out" else R[a])
                for kk, v in r.items(): tot[kk] = tot.get(kk, 0) + v
            worst = max(worst, np.sqrt(sum(abs(v)**2 for v in tot.values())))
    return worst
res_own = np.array([own_resid(k, v) for k, v in zip(ks, vs)])
out["bad_gauss_min_own"] = float(res_own.min()); out["bad_gauss_max_own"] = float(res_own.max())
out["bad_gauss_lib_vs_own_maxdiff"] = float(np.abs(res_own - res_lib).max())
# physical gauss
resp = []
for i in physidx:
    k, v = enc.decode_state(np.array([allc[i]]), np.array([1.0+0j])); resp.append(own_resid(k, v))
out["phys_gauss_max_own"] = float(max(resp))
# --- physical codes: decode == gauge*route-A
dev = 0; 
for i in physidx:
    c = allc[i]; k = enc.decode(c)
    kk, vv = enc.decode_state(np.array([c]), np.array([1.0+0j]))
    ref = dict(zip(basis.keys[k].tolist(), (basis.amps[k]*enc.gauge[k]).tolist()))
    got = dict(zip(kk.tolist(), vv.tolist()))
    for key in set(ref)|set(got):
        dev = max(dev, abs(ref.get(key,0)-got.get(key,0)))
out["phys_decode_vs_gauge_times_routeA_maxdev"] = float(dev)
# gauge: real +-1 and independent gauge_align
HA, _ = h_magnetic_phys(basis)
HB = enc.h_magnetic()
D, res = gauge_align(HA, HB)
out["gauge_res"] = float(res); out["gauge_matches"] = bool(np.abs(D.real - enc.gauge).max() < 1e-12 or np.abs(D.real + enc.gauge).max() < 1e-12)
out["gauge_nminus"] = int((enc.gauge < 0).sum())
out["H_A_eq_D_HB_D_maxdev"] = float(np.abs(HA - np.diag(enc.gauge) @ HB @ np.diag(enc.gauge)).max())
# --- naive prototype fallback (m = +-1/2 on every end) overlap with physical states
def naive(code):
    j = [(code >> l) & 1 for l in range(4)] + [(code >> (8 + k)) & 1 for k in range(8)]
    bit = [(code >> (4 + c)) & 1 for c in range(4)]; key = 0
    for i in range(12):
        if not j[i]: continue
        mL = mR = 0.5
        for c, corner in enumerate(basis.diagram.corners):
            for li, role in corner.ends:
                if li == i:
                    m = -0.5 if bit[c] else 0.5
                    if role == "out": mL = m
                    else: mR = m
        key += ls.index[(0.5, mL, mR)] * 5**i
    return key
Pm = sp.csr_matrix((np.concatenate(basis.amps), (np.searchsorted(uk, np.concatenate(basis.keys)) if False else np.zeros(0,int), np.zeros(0,int))), shape=(1,1)) if False else None
keymap = {}
allk = np.concatenate(basis.keys); ukk, invk = np.unique(allk, return_inverse=True)
colk = np.concatenate([np.full(len(k), i) for i, k in enumerate(basis.keys)])
P = sp.csr_matrix((np.concatenate(basis.amps), (invk, colk)), shape=(len(ukk), 433))
ov = []
for i in badidx:
    key = naive(allc[i]); p = np.searchsorted(ukk, key)
    row = P[p].toarray().ravel() if p < len(ukk) and ukk[p] == key else np.zeros(433)
    ov.append(np.linalg.norm(row))
ov = np.array(ov)
out["naive_fallback_n_overlap_gt1e-12"] = int((ov > 1e-12).sum()); out["naive_fallback_max_overlap"] = float(ov.max())
# --- K from route B
K = enc.K_codes
bright = [i for i, c in enumerate(inner) if c >> 4 == 0]
pairs = {}
rowsK = []
for i in range(47):
    nz = np.flatnonzero(np.abs(K[i]) > 1e-12)
    rowsK.append(nz.tolist())
dark = [i for i in range(47) if len(rowsK[i]) == 0]
pairs = sorted({tuple(sorted((i, rowsK[i][0]))) for i in range(47) if len(rowsK[i]) == 1})
out["K_dark_rows"] = len(dark); out["K_n_pairs"] = len(pairs)
out["K_rows_with_not_exactly_one_nz"] = sum(1 for i in range(47) if len(rowsK[i]) not in (0, 1))
out["K_pair_couplings"] = sorted(float(K[a, b]) for a, b in pairs)
out["K_pair_partner_is_xor15"] = all(inner[a] ^ inner[b] == 15 for a, b in pairs)
out["K_symmetric_real"] = float(np.abs(K - K.T).max()), float(np.abs(K.imag).max())
out["K_matches_Kinner_perm"] = None
# --- route-B target vs route A after gauge_align, beta in {0.61, 1.0}
for beta in (0.61, 1.0):
    VB = enc.target("UB", None, beta)
    VA = targetA(basis, "UB", None, beta)
    D2, r2 = gauge_align(VA, VB)
    out[f"UB_B_vs_A_gauge_align_res_beta{beta}"] = float(r2)
    out[f"UB_B_vs_expm_HB_beta{beta}"] = float(np.abs(VB - sl.expm(-1j*beta*HB)).max())
    out[f"UB_unitarity_beta{beta}"] = float(np.abs(VB.conj().T@VB - np.eye(433)).max())
    out[f"UB_B_eq_Dag_VA_D_beta{beta}"] = float(np.abs(VB - np.diag(enc.gauge)@VA@np.diag(enc.gauge)).max())
    # inner target consistency: every outer-pattern block
    VI = enc.inner_target("UB", None, beta)
    outer = (enc._codes >> 8)
    dev = 0
    for o in np.unique(outer):
        idx = np.flatnonzero(outer == o)
        pos = enc._pos_of_k[idx]
        dev = max(dev, np.abs(VB[np.ix_(idx, idx)] - VI[np.ix_(pos, pos)]).max())
    # cross-outer blocks zero
    mask = outer[:, None] != outer[None, :]
    out[f"UB_inner_block_consistency_beta{beta}"] = float(dev); out[f"UB_cross_outer_max_beta{beta}"] = float(np.abs(VB[mask]).max())
    out[f"inner_UB_vs_expm_K_beta{beta}"] = float(np.abs(VI - sl.expm(-1j*beta*K)).max())
alpha, beta = 0.37, 0.61
for order in (1, 2):
    S = enc.target("step", alpha, beta, order); SI = enc.inner_target("step", alpha, beta, order)
    outer = (enc._codes >> 8); dev = 0
    for o in np.unique(outer):
        idx = np.flatnonzero(outer == o); pos = enc._pos_of_k[idx]
        dev = max(dev, np.abs(S[np.ix_(idx, idx)] - SI[np.ix_(pos, pos)]).max())
    out[f"step_inner_consistency_order{order}"] = float(dev)
    SA = targetA(basis, "step", alpha, beta, order); D2, r2 = gauge_align(SA, S)
    out[f"step_B_vs_A_gauge_res_order{order}"] = float(r2)
UE = enc.target("UE", 0.37, None); UEA = targetA(basis, "UE", 0.37)
out["UE_B_vs_A"] = float(np.abs(UE - UEA).max())
UEo = enc.target("UE", 0.37, None, include_outer_electric=True); UEAo = targetA(basis, "UE", 0.37, include_outer_electric=True)
out["UE_outer_B_vs_A"] = float(np.abs(UEo - UEAo).max())
UI = enc.inner_target("UE", 0.37, None); out["UE_inner_consistency"] = float(max(np.abs(np.diag(UE)[np.flatnonzero(outer==o)] - np.diag(UI)[enc._pos_of_k[np.flatnonzero(outer==o)]]).max() for o in np.unique(outer)))
# regauge
rng = np.random.default_rng(7); Dg = rng.choice([-1., 1.], 47)
VR = enc.regauge(enc.target("UB", None, 0.61), Dg)
Dm = Dg[enc._pos_of_k]
out["regauge_dev"] = float(np.abs(VR - Dm[:,None]*enc.target("UB",None,0.61)*Dm[None,:]).max())
# identity evaluate
from qiskit import QuantumCircuit, QuantumRegister
from su2plaq.evaluate.evaluator import evaluate
qc = QuantumCircuit(QuantumRegister(8, "d"))
v = evaluate(qc, enc, enc.target("UE", 0.0, None))
out["evaluate_identity_UE0"] = dict(ok=bool(v.ok), err=float(v.op_norm_error), gauss=float(v.gauss_residual), leak=float(getattr(v,"leak",float("nan"))))
# align_inner_block with a gauge
VI = enc.inner_target("UB", None, 0.61); Dd = rng.choice([-1., 1.], 47)
Dgot, r, ph = enc.__class__.__module__ and __import__("su2plaq.encodings.spinnet", fromlist=["x"]).align_inner_block(np.exp(0.3j)*(Dd[:,None]*VI*Dd[None,:]), VI)
out["align_inner_block_res"] = float(r)
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
for k, v in out.items(): print(k, v)
