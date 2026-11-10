"""Tester 203 item 4: observables from scratch.  Rishon: own sparse 16-mode JW, W = Tr(U_b U_r U_t^dag U_l^dag), own 1296 codes,
H_B = -(W+W^dag), H_E = 3/4 #Q, vacuum vac_A (b,r type A; t,l type B), U_1 = exp(-i beta H_B) exp(-i alpha H_E) (scipy expm_multiply, not production).
KS: independent closed 2x2 blocks H_B=[[0,-2],[-2,0]], H_E=diag(0,3) in (vacuum, all-half loop) [METHODS sec 4]; plus the production
laptop 433-dim target used as a cross-check by the acceptance test (not repeated here)."""
import itertools, json, subprocess, sys
import numpy as np, scipy.sparse as sp
from scipy.linalg import expm
from scipy.sparse.linalg import expm_multiply
sys.path.insert(0, "src")
from su2plaq.rishon.observables import observables, closed_forms, closed_spectra, observables_table

N = 16
I2 = sp.identity(2, format="csr"); Zm = sp.diags([1.0, -1.0]); SM = sp.csr_matrix(np.array([[0, 1], [0, 0]], float))   # sigma^- = |0><1|
def kron_le(ops):
    out = sp.identity(1, format="csr")
    for o in ops: out = sp.kron(o, out, format="csr")   # ops[0] = qubit 0 least significant
    return out
c = [kron_le([Zm] * k + [SM] + [I2] * (N - k - 1)) for k in range(N)]
cd = [m.T.tocsr() for m in c]
def U(l, i, j):   # U_ij = c_{L,i} c^dag_{R,j}; L1=4l,L2=4l+1,R1=4l+2,R2=4l+3
    return c[4 * l + i] @ cd[4 * l + 2 + j]
b_, r_, t_, l_ = 0, 1, 2, 3
W = sp.csr_matrix((2 ** N, 2 ** N), dtype=complex)
for a, b, cc, d in itertools.product(range(2), repeat=4):
    W = W + U(b_, a, b) @ U(r_, b, cc) @ U(t_, d, cc).T.conj() @ U(l_, a, d).T.conj()
codes = np.array(sorted(sum(cd_ << (4 * l) for l, cd_ in enumerate(cfg)) for cfg in itertools.product([3, 5, 6, 9, 10, 12], repeat=4)))
Wc = W[codes][:, codes]
leak = abs(W[codes].sum() - Wc.sum())
HB = -(Wc + Wc.T.conj()).toarray()
nQ = np.array([sum((int(x) >> (4 * l)) & 15 in (5, 6, 9, 10) for l in range(4)) for x in codes])
HE = 0.75 * nQ
va = 3 | (3 << 4) | (12 << 8) | (12 << 12)    # b,r = A (1100 -> 3), t,l = B (0011 -> 12)
i0 = int(np.searchsorted(codes, va))
rec = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "W_leak_outside_codes": float(leak),
       "HB_vac_expect": float(HB[i0, i0]), "TrU_P_vacA_norm": float(np.linalg.norm(HB[:, i0]))}
def mine_rishon(alpha, beta, nsteps=2):
    psi = np.zeros(len(codes), complex); psi[i0] = 1
    out = {}
    for n in range(1, nsteps + 1):
        psi = expm_multiply(-1j * beta * HB, np.exp(-1j * alpha * HE) * psi)
        p = np.abs(psi) ** 2
        out[n] = dict(E_link=float(0.25 * (p @ HE)), P=float(-0.5 * np.real(psi.conj() @ (HB @ psi))), echo=float(abs(psi[i0]) ** 2))
    return out
HBk = np.array([[0, -2], [-2, 0]], float); HEk = np.diag([0, 3.0])
def mine_ks(alpha, beta, nsteps=2):
    psi = np.array([1, 0], complex); out = {}
    Uk = expm(-1j * beta * HBk) @ expm(-1j * alpha * HEk)
    for n in range(1, nsteps + 1):
        psi = Uk @ psi; p = np.abs(psi) ** 2
        out[n] = dict(E_link=float(0.25 * (p @ np.diag(HEk))), P=float(-0.5 * np.real(psi.conj() @ (HBk @ psi))), echo=float(abs(psi[0]) ** 2))
    return out
rec["angles"] = {}
worst = 0.0
for (a, b) in ((0.37, 0.61), (0.91, 0.23), (1.7, 1.0)):
    prod = observables(a, b, n_steps=2)
    mr, mk = mine_rishon(a, b), mine_ks(a, b)
    row = {}
    for th, mine in (("rishon", mr), ("ks", mk)):
        for n in (1, 2):
            for k in ("E_link", "P", "echo"):
                d = abs(prod[th][n][k] - mine[n][k]); worst = max(worst, d)
                row[f"{th}_n{n}_{k}"] = dict(prod=prod[th][n][k], own=mine[n][k], diff=d)
    cf = closed_forms(a, b)
    # own closed form
    tk, tr = 2 * b, 4 * np.sqrt(2) * b
    own_cf = dict(ks_E=0.75 * np.sin(tk) ** 2, ks_L=np.cos(tk) ** 2, r_E=0.375 * np.sin(tr) ** 2, r_L=0.25 * (1 + np.cos(tr)) ** 2)
    row["closed_form_diff"] = max(abs(cf["ks"]["E_link"] - own_cf["ks_E"]), abs(cf["ks"]["echo"] - own_cf["ks_L"]),
                                  abs(cf["rishon"]["E_link"] - own_cf["r_E"]), abs(cf["rishon"]["echo"] - own_cf["r_L"]))
    row["own_vs_closed_form_n1"] = max(abs(mr[1]["E_link"] - own_cf["r_E"]), abs(mr[1]["echo"] - own_cf["r_L"]), abs(mk[1]["E_link"] - own_cf["ks_E"]), abs(mk[1]["echo"] - own_cf["ks_L"]))
    rec["angles"][f"{a},{b}"] = row
rec["worst_prod_vs_own"] = worst
# closed spectra vs own formula
sp_ = closed_spectra((0.5, 1.0, 2.0)); sd = 0.0
for g2 in (0.5, 1.0, 2.0):
    r = np.sort(np.array([0.0, 0.75 * g2 + np.sqrt(9 / 16 * g2 ** 2 + 32 / g2 ** 2), 0.75 * g2 - np.sqrt(9 / 16 * g2 ** 2 + 32 / g2 ** 2)]))
    k = np.sort(np.array([0.75 * g2 + np.sqrt(9 / 16 * g2 ** 2 + 4 / g2 ** 2), 0.75 * g2 - np.sqrt(9 / 16 * g2 ** 2 + 4 / g2 ** 2)]))
    # own diag of 3x3 / 2x2 from my H blocks:  H = g2/2 H_E + H_B/g2 on the closed subspace
    # closed rishon block in {vacA, loop, vacB}: loop = state with HB column; build from my HB: Krylov from vacA
    v = HB[:, i0] / np.linalg.norm(HB[:, i0]); w2 = HB @ v; w2 = w2 - (w2 @ v) * v - (w2 @ np.eye(len(codes))[i0]) * np.eye(len(codes))[i0]
    e0 = np.zeros(len(codes)); e0[i0] = 1
    # orthonormal basis {vacA, loop (=normalised H_B vacA), vacB = remaining normalised part of H_B loop}
    loop = v; Hl = HB @ loop; vb = Hl - (Hl @ e0) * e0 - (Hl @ loop) * loop; nb = np.linalg.norm(vb); vb /= nb
    B3 = np.stack([e0, loop, vb], 1)
    H3 = g2 / 2 * (B3.T @ (HE[:, None] * B3)) + (B3.T @ HB @ B3) / g2
    own_r = np.sort(np.linalg.eigvalsh(H3))
    e = np.array(sp_["rishon"][g2]["eigenvalues"]); m = sp_["rishon"][g2]["multiplicities"]
    sd = max(sd, np.abs(np.sort(e) - own_r).max(), np.abs(own_r - r).max())
    ek = np.array(sp_["ks"][g2]["eigenvalues"]); own_k = np.sort(np.linalg.eigvalsh(g2 / 2 * HEk + HBk / g2))
    sd = max(sd, np.abs(np.sort(ek) - own_k).max(), np.abs(own_k - k).max())
    rec.setdefault("rishon_mult", {})[str(g2)] = m
    rec.setdefault("own_H3_offdiag_norm", {})[str(g2)] = float(np.linalg.norm(B3.T @ HB @ B3 - np.array([[0, -4, 0], [-4, 0, -4], [0, -4, 0]])))
rec["spectra_worst_dev"] = float(sd)
# table JSON-able
tab = observables_table(); json.dumps(tab)
rec["table_keys"] = sorted(tab)
print(json.dumps(rec, indent=1, default=float)[:3500])
json.dump(rec, open("results/rishon/tester-203-observables-independent.json", "w"), indent=1, default=float)
