"""Tester 222 (rishon D1+D2): independent construction of the det term and the three-layer targets.

Only numpy / scipy here; the JW link algebra, W, H_E, H_B, H_D, U_D, U_B, U_E and both Trotter orders are built from scratch
(METHODS-rishon R1, R2, R4, R13 conventions).  Production is imported only AFTER my own numbers exist, to compare.
Run: python results/rishon/tester-222-det-independent.py  (PYTHONPATH=src).  Output: results/rishon/tester-222-det-independent.json
"""
import itertools, json, subprocess, sys, time, importlib.util
import numpy as np
from scipy.linalg import expm

t00 = time.time()
rec = {"checks": {}}
SECTOR = [3, 5, 6, 9, 10, 12]                      # bits L1 L2 R1 R2 -> L1 + 2 L2 + 4 R1 + 8 R2


# ---------------- own JW on one link (4 modes = 4 qubits, little-endian, c_k = Z...Z sigma^-_k) ----------------
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1:
            sign = (-1) ** sum((n >> m) & 1 for m in range(k))
            M[n ^ (1 << k), n] = sign
    return M


c = [c_op(k) for k in range(4)]
cd = [m.T for m in c]
# CAR check
car = max(np.abs(c[i] @ cd[j] + cd[j] @ c[i] - (i == j) * np.eye(16)).max() for i in range(4) for j in range(4))
car = max(car, max(np.abs(c[i] @ c[j] + c[j] @ c[i]).max() for i in range(4) for j in range(4)))
rec["checks"]["CAR_max_dev"] = car
# modes: L1=0 L2=1 R1=2 R2=3 ;  U_ij = c_{L,i} c^dag_{R,j}
def U(i, j):
    return c[i] @ cd[2 + j]

detU_diff = U(0, 0) @ U(1, 1) - U(0, 1) @ U(1, 0)
detU_prod = 2 * c[0] @ cd[2] @ c[1] @ cd[3]
rec["checks"]["detU_diff_vs_2cLcRcLcR"] = float(np.abs(detU_diff - detU_prod).max())
nz = np.argwhere(np.abs(detU_diff) > 1e-14)
rec["checks"]["detU_nonzeros"] = [[int(a), int(b), float(detU_diff[a, b])] for a, b in nz]   # expect (12, 3, +2): B <- A
HD_link = detU_diff + detU_diff.T
ev = np.linalg.eigvalsh(HD_link)
rec["checks"]["HD_link_eigs_nonzero"] = [float(x) for x in ev if abs(x) > 1e-12]
rec["checks"]["HD_link_nzero"] = int(sum(abs(x) < 1e-12 for x in ev))
# 2(|B><A| + |A><B|)
ref = np.zeros((16, 16)); ref[12, 3] = ref[3, 12] = 2.0
rec["checks"]["HD_link_vs_2(BA+AB)"] = float(np.abs(HD_link - ref).max())
# eigenvectors: +2 on (A+B)/sqrt2, -2 on (A-B)/sqrt2
vp = np.zeros(16); vp[3] = vp[12] = 1 / np.sqrt(2)
vm = np.zeros(16); vm[3] = 1 / np.sqrt(2); vm[12] = -1 / np.sqrt(2)
rec["checks"]["HD_link_eigvec_plus"] = float(np.linalg.norm(HD_link @ vp - 2 * vp))
rec["checks"]["HD_link_eigvec_minus"] = float(np.linalg.norm(HD_link @ vm + 2 * vm))
# the quartet codes are annihilated
rec["checks"]["HD_link_quartet_annihilated"] = float(np.abs(HD_link[:, [5, 6, 9, 10]]).max())
# sector preserved
other = [x for x in range(16) if x not in SECTOR]
rec["checks"]["detU_leaves_sector"] = float(np.abs(detU_diff[np.ix_(other, SECTOR)]).max())

# ---------------- sector blocks and inner 1296 operators (row-major kron(link3, link2, link1, link0)) ----------------
def res(M):
    return M[np.ix_(SECTOR, SECTOR)]


Ub = [[res(U(i, j)) for j in range(2)] for i in range(2)]
Ud = [[res(U(i, j)).T for j in range(2)] for i in range(2)]      # Ud[i][j] = (U_ij)^dag = U_ij^T (real); (U^dag)_cd = (U_dc)^dag
detb = res(detU_diff)


def kron4(ms):
    out = np.ones((1, 1))
    for m in ms:                                    # link 0 least significant
        out = np.kron(m, out)
    return out


W = np.zeros((1296, 1296))
for a, b, cc, d in itertools.product(range(2), repeat=4):
    # W = Tr(U_b U_r U_t^dag U_l^dag): (U_b)_ab (U_r)_bc (U_t^dag)_cd (U_l^dag)_da, (U^dag)_cd = (U_dc)^dag
    W += kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]])
HB = -(W + W.T)
HDin = sum(kron4([(detb + detb.T) if l == k else np.eye(6) for l in range(4)]) for k in range(4))
# H_E = 3/4 * (#Q links): Casimir 1/2 sum_a (L_a^2+R_a^2) per link; evaluate it from the algebra instead of assuming 3/4
sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
def gen(a, pair):                                   # pair = (mode0, mode1) of the end; sum_ij (T_a)_ij c^dag_i c_j
    return sum((sig[a][i, j] / 2) * cd[pair[i]] @ c[pair[j]] for i in range(2) for j in range(2))
cas = 0.5 * sum(gen(a, (0, 1)) @ gen(a, (0, 1)) + gen(a, (2, 3)) @ gen(a, (2, 3)) for a in range(3))
cas_s = np.real(np.diag(res(cas)))
rec["checks"]["casimir_on_sector"] = [float(x) for x in cas_s]            # expect 0, 3/4 x4, 0
nQ = np.zeros(1296)
for idx in range(1296):
    for l in range(4):
        s = (idx // 6 ** l) % 6
        nQ[idx] += cas_s[s]
HE = nQ                                             # diagonal
HEm = np.diag(HE)

comm_DE = HDin @ HEm - HEm @ HDin
rec["checks"]["[H_D,H_E]_maxabs"] = float(np.abs(comm_DE).max())
t = time.time()
C = HDin @ HB - HB @ HDin
sv = np.linalg.svd(C, compute_uv=False)
rec["checks"]["||[H_D,H_B]||_2"] = float(sv[0]); rec["checks"]["16sqrt2"] = float(16 * np.sqrt(2))
rec["checks"]["||[H_D,H_B]||_2 - 16sqrt2"] = float(sv[0] - 16 * np.sqrt(2))
rec["checks"]["HB_spectrum_rounded"] = {str(k): int(v) for k, v in zip(*np.unique(np.round(np.linalg.eigvalsh(HB), 6), return_counts=True))}
rec["checks"]["HD_in_spectrum"] = {str(k): int(v) for k, v in zip(*np.unique(np.round(np.linalg.eigvalsh(HDin), 6), return_counts=True))}
rec["checks"]["HD_in_symmetric"] = float(np.abs(HDin - HDin.T).max())

# ---------------- sign of lambda_D: S = prod_l exp(i pi/4 (n_R - n_L)_l) ----------------
nRL = np.array([((n >> 2) & 1) + ((n >> 3) & 1) - (n & 1) - ((n >> 1) & 1) for n in range(16)], float)
sd = np.exp(1j * np.pi / 4 * nRL[SECTOR])           # diagonal of S on the sector (16x? no: 6 codes)
Sin = np.ones(1)
for l in range(4):
    Sin = np.kron(sd, Sin)
S = np.diag(Sin)
rec["checks"]["S_unitary"] = float(np.abs(S @ S.conj().T - np.eye(1296)).max())
rec["checks"]["S HD S^dag + HD"] = float(np.abs(S @ HDin @ S.conj().T + HDin).max())
rec["checks"]["S HE S^dag - HE"] = float(np.abs(S @ HEm @ S.conj().T - HEm).max())
rec["checks"]["S HB S^dag - HB"] = float(np.abs(S @ HB @ S.conj().T - HB).max())
# consequence: spectrum of H(lam) equals spectrum of H(-lam)
g2 = 1.1014
e_p = np.linalg.eigvalsh(g2 / 2 * HEm + HB / g2 + 0.4316 * HDin)
e_m = np.linalg.eigvalsh(g2 / 2 * HEm + HB / g2 - 0.4316 * HDin)
rec["checks"]["spec H(+lam) vs H(-lam)"] = float(np.abs(e_p - e_m).max())

# ---------------- three-layer targets, own composition ----------------
wB, VB = np.linalg.eigh(HB)
def UB(beta): return (VB * np.exp(-1j * beta * wB)) @ VB.T
def UE(alpha): return np.diag(np.exp(-1j * alpha * HE))
wD, VD = np.linalg.eigh(HDin)
def UD(eta): return (VD * np.exp(-1j * eta * wD)) @ VD.T
# cross-check own eigh-based U_B against scipy expm at one value
rec["checks"]["UB_eigh_vs_expm(0.61)"] = float(np.abs(UB(0.61) - expm(-1j * 0.61 * HB)).max())
rec["checks"]["UD_eigh_vs_expm(0.29)"] = float(np.abs(UD(0.29) - expm(-1j * 0.29 * HDin)).max())
# closed form of U_D (tensor over links of 1 + (cos2eta-1)(AA+BB) - i sin2eta (AB+BA))
def ud_closed(eta):
    P = np.zeros((6, 6)); P[0, 0] = P[5, 5] = 1                # sector order [3,5,6,9,10,12]: A = idx 0, B = idx 5
    X = np.zeros((6, 6)); X[0, 5] = X[5, 0] = 1
    lay = np.eye(6) + (np.cos(2 * eta) - 1) * P - 1j * np.sin(2 * eta) * X
    out = np.ones((1, 1))
    for _ in range(4):
        out = np.kron(lay, out)
    return out
rec["checks"]["UD_closed_form_vs_eigh(0.29)"] = float(np.abs(ud_closed(0.29) - UD(0.29)).max())
rec["checks"]["[UD,UE]"] = float(np.abs(UD(0.53) @ UE(0.91) - UE(0.91) @ UD(0.53)).max())
rec["checks"]["[UD,UB]_nonzero"] = float(np.abs(UD(0.53) @ UB(0.23) - UB(0.23) @ UD(0.53)).max())

def own_U1(a, b, e): return UB(b) @ UD(e) @ UE(a)
def own_U2(a, b, e):
    half = UE(a / 2) @ UD(e / 2)
    return half @ UB(b) @ (UD(e / 2) @ UE(a / 2))
rec["triples"] = [[0.37, 0.61, 0.29], [0.91, 0.23, 0.53], [1.70, 1.00, 1.07]]
for T in rec["triples"]:
    a, b, e = T
    rec[f"own_U1_{T}_unitary"] = float(np.abs(own_U1(a, b, e).conj().T @ own_U1(a, b, e) - np.eye(1296)).max())
    rec[f"own_U1_vs_U2_{T}"] = float(np.linalg.norm(own_U1(a, b, e) - own_U2(a, b, e), 2))

# ---------------- local error slopes ----------------
g2, lamd = 1.1014, 0.4316
H = g2 / 2 * HEm + HB / g2 + lamd * HDin
wH, VH = np.linalg.eigh(H)
def Uex(dt): return (VH * np.exp(-1j * dt * wH)) @ VH.T
slopes = {}
for order, f in ((1, own_U1), (2, own_U2)):
    errs = []
    dts = (0.1, 0.05, 0.025, 0.0125)
    for dt in dts:
        a, b, e = g2 * dt / 2, dt / g2, lamd * dt
        errs.append(float(np.linalg.norm(f(a, b, e) - Uex(dt), 2)))
    sl = [float(np.log(errs[i] / errs[i + 1]) / np.log(2)) for i in range(len(dts) - 1)]
    slopes[str(order)] = {"dts": list(dts), "errs": errs, "slopes": sl}
rec["slopes"] = slopes
rec["checks"]["own_H_time"] = time.time() - t00

# ---------------- compare with production ----------------
sys.path.insert(0, "src")
from su2plaq.rishon import operators as ops
prod = {}
prod["h_det_inner_vs_own"] = float(np.abs(ops.h_det_inner() - HDin).max())
prod["h_det_inner_dtype"] = str(ops.h_det_inner().dtype)
prod["det_term_inner_vs_h_det_inner"] = float(np.abs(ops.det_term_inner() - ops.h_det_inner()).max())
prod["H_B_vs_own"] = float(np.abs(ops.h_magnetic_inner() - HB).max())
prod["H_E_vs_own"] = float(np.abs(ops.h_electric_inner() - HE).max())
prod["hamiltonian_inner(1.1014,0.4316)_vs_own"] = float(np.abs(ops.hamiltonian_inner(g2, lamd) - H).max())
prod["hamiltonian_inner(g2)_default_lam0_vs_own"] = float(np.abs(ops.hamiltonian_inner(g2) - (g2 / 2 * HEm + HB / g2)).max())
for T in rec["triples"]:
    a, b, e = T
    prod[f"UD({e})"] = float(np.abs(ops.inner_target("UD", a, b, eta=e) - UD(e)).max())
    prod[f"U1{T}"] = float(np.abs(ops.inner_target("step", a, b, 1, eta=e) - own_U1(a, b, e)).max())
    prod[f"U2{T}"] = float(np.abs(ops.inner_target("step", a, b, 2, eta=e) - own_U2(a, b, e)).max())
    prod[f"U1{T}_unitary"] = float(np.abs(ops.inner_target("step", a, b, 1, eta=e).conj().T @ ops.inner_target("step", a, b, 1, eta=e) - np.eye(1296)).max())
    # production wrong-order discrimination: UE UD UB (det layer after magnetic) must differ strongly
    prod[f"wrong_order_UE_UD_UB{T}_vs_prod_U1"] = float(np.linalg.norm(UE(a) @ UD(e) @ UB(b) - ops.inner_target("step", a, b, 1, eta=e), 2))
# eta=0 limit: array_equal with the old targets (HEAD's operators.py loaded under another name)
old_src = subprocess.run(["git", "show", "HEAD:src/su2plaq/rishon/operators.py"], capture_output=True, text=True, check=True).stdout
import types
old = types.ModuleType("old_operators"); exec(compile(old_src, "old_operators.py", "exec"), old.__dict__)
ident = {}
for order in (1, 2):
    for (a, b) in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
        o = old.inner_target("step", a, b, order)
        n_none = ops.inner_target("step", a, b, order)
        n_zero = ops.inner_target("step", a, b, order, eta=0.0)
        ident[f"order{order}_{a}_{b}"] = {"eta_None_array_equal_old": bool(np.array_equal(o, n_none)),
                                         "eta_0_array_equal_old": bool(np.array_equal(o, n_zero)),
                                         "eta_0_maxdiff": float(np.abs(o - n_zero).max())}
for kind, a, b in (("UE", 0.37, None), ("UB", None, 0.61)):
    ident[kind] = bool(np.array_equal(old.inner_target(kind, a, b), ops.inner_target(kind, a, b)))
ident["closed_block_full(g2)_old_vs_new_lam0"] = [bool(np.array_equal(old.closed_block_full(g), ops.closed_block_full(g))) for g in (0.5, 1.0, 2.0)]
ident["closed_block_full(g2, 0.0)_equal"] = [bool(np.array_equal(old.closed_block_full(g), ops.closed_block_full(g, 0.0))) for g in (0.5, 1.0, 2.0)]
prod["identity_with_HEAD"] = ident
# error handling
errs = {}
for name, fn in (("UD_eta_None", lambda: ops.inner_target("UD", 0.1, 0.1)),
                 ("UE_with_eta", lambda: ops.inner_target("UE", 0.1, None, eta=0.2)),
                 ("UB_with_eta", lambda: ops.inner_target("UB", None, 0.1, eta=0.2)),
                 ("step_order3", lambda: ops.inner_target("step", 0.1, 0.1, 3, eta=0.2))):
    try:
        fn(); errs[name] = "NO ERROR"
    except ValueError as ex:
        errs[name] = "ValueError"
    except Exception as ex:
        errs[name] = type(ex).__name__
prod["error_handling"] = errs
# closed 17x17 block with det vs own Krylov block
vac = np.zeros(1296)
# vac_A: inner b,r type A (sector idx 0), t,l type B (idx 5); link 0 least significant
idxA = 0 * 1 + 0 * 6 + 5 * 36 + 5 * 216
vac[idxA] = 1
res17 = {}
for g in (0.5, 1.0, 2.0):
    for lam in (0.0, 0.2, 0.5):
        Hh = g / 2 * HEm + HB / g + lam * HDin
        K = [vac]
        Q_, _ = np.linalg.qr(np.array(K).T)
        basis = Q_
        for _ in range(8):
            new = np.concatenate([basis, Hh @ basis], axis=1)
            u, s, _ = np.linalg.svd(new, full_matrices=False)
            basis = u[:, s > 1e-9]
        dim = basis.shape[1]
        own_ev = np.sort(np.linalg.eigvalsh(basis.T @ Hh @ basis))
        pv = np.sort(np.linalg.eigvalsh(ops.closed_block_full(g, lam)))
        res17[f"g2={g},lam={lam}"] = {"krylov_dim": int(dim), "max_eig_diff": float(np.abs(own_ev - pv).max()) if dim == 17 else None,
                                      "n_zero_levels_own": int(np.sum(np.abs(own_ev) < 1e-9))}
prod["closed_block_full_vs_own_krylov"] = res17
rec["production_comparison"] = prod
rec["wall_s"] = time.time() - t00
rec["git"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
rec["git_dirty_note"] = "builder D1/D2 changes uncommitted at test time"
json.dump(rec, open("results/rishon/tester-222-det-independent.json", "w"), indent=1)
print(json.dumps(rec, indent=1)[:12000])
