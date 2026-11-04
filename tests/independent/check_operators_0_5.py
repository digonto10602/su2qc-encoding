"""Independent verification of M0 step 0.5 (exact operators W, H_E, H_B, targets).  Tester script, not collected by pytest.
Uses su2plaq only to read the objects under test (basis.keys/amps/labels as input vectors; plaquette_W, h_magnetic_phys,
hamiltonian_phys, target as the things being compared).  Own U matrices, own W contraction, own Psi-contraction, own expm.
Run: python tests/independent/check_operators_0_5.py   (deterministic, no RNG; seed recorded as 0)"""
import itertools, json, subprocess, sys, time
import numpy as np
import scipy.sparse as sp
from scipy.linalg import expm

sys.path.insert(0, "src")
from su2plaq.exact import physical as P
from su2plaq.exact import operators as O
from su2plaq.su2.algebra import LinkSpace

out = {"seed": None, "commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip(),
       "note": "step files uncommitted at HEAD", "alpha": 0.37, "beta": 0.61}
al, be = 0.37, 0.61

# ------------------------------------------------------------------ own link matrices (5 dim, order 0,++,+-,-+,--)
r2 = 1 / np.sqrt(2)
eps = np.array([[0, 1], [-1, 0]])
idx = lambda k, l: 1 + 2 * k + l
Ucg = np.zeros((2, 2, 5, 5), complex)  # [i,j] -> 5x5 matrix, U_ij = D^{1/2}_{ij}, states sqrt(2j+1) D^j_{mL mR}, jmax=1/2 projection
for i in range(2):
    for j in range(2):
        Ucg[i, j, idx(i, j), 0] = r2                      # D_ij * 1 = (1/sqrt2) |1/2; i j>
        for k in range(2):
            for l in range(2):
                Ucg[i, j, 0, idx(k, l)] = eps[i, k] * eps[j, l] * r2   # singlet part of D_ij D_kl = (1/2) eps_ik eps_jl
# Paulo Eq. 28 (rewritten by me): U_ab |a b> = |0>/sqrt2 ; U_ab |0> = s(a)s(b)|abar bbar>/sqrt2
s_ = [1, -1]
Upa = np.zeros((2, 2, 5, 5), complex)
for a in range(2):
    for b in range(2):
        Upa[a, b, 0, idx(a, b)] = r2
        Upa[a, b, idx(1 - a, 1 - b), 0] = r2 * s_[a] * s_[b]

def own_W(U):
    """W = sum U_b[a,b] U_r[b,c] (U_t^dag)[c,d] (U_l^dag)[d,a];  (U^dag)[c,d] = (U[d,c])^dagger (operator adjoint).
    axes of result: (l',t',r',b', l,t,r,b) so that C-order flatten gives link 0 (b) least significant."""
    Ud = np.einsum("dcxy->cdyx", U).conj()  # (U^dag)[c,d][x,y] = conj(U[d,c][y,x])
    # explicit, readable version
    T = np.zeros((5,) * 8, complex)  # [l',t',r',b', l,t,r,b]
    for a, b, c, d in itertools.product(range(2), repeat=4):
        Mb, Mr, Mt, Ml = U[a, b], U[b, c], Ud[c, d], Ud[d, a]
        T += np.einsum("ij,kl,mn,op->ikmojlnp", Ml, Mt, Mr, Mb)
    return T.reshape(625, 625)

t0 = time.time()
W_cg_own = own_W(Ucg)
W_pa_own = own_W(Upa)
out["W_build_s"] = time.time() - t0
W_cg = O.plaquette_W(convention="cg")
W_pa = O.plaquette_W(convention="paulo")
d_cg = np.abs(W_cg - W_cg_own).max()
d_pa = np.abs(W_pa - W_pa_own).max()
print(f"(1) max|plaquette_W(cg)    - W_own(cg)|    = {d_cg:.2e}")
print(f"(1) max|plaquette_W(paulo) - W_own(paulo)| = {d_pa:.2e}")
# own U check against LinkSpace.U (the builder's CG U)
Ub = LinkSpace(0.5).U()
dU = max(np.abs(Ub[i][j] - Ucg[i, j]).max() for i in range(2) for j in range(2))
print(f"    max|LinkSpace.U - own hand-built cg U| = {dU:.2e}")
# check own U properties: sum_k U_ik U_jk^dag-type unitarity-ish not exact after truncation; check det-like identity skip
# Eq 37: W|0000>
for name, Wm in (("cg", W_cg), ("paulo", W_pa)):
    col = Wm[:, 0]
    nz = np.abs(col) > 1e-12
    mags = np.abs(col[nz])
    print(f"    {name}: W|0000>: norm={np.linalg.norm(col):.15f}, #nonzero={nz.sum()}, |amp| min/max = {mags.min():.6f}/{mags.max():.6f}, all inner j=1/2 (no idx 0): "
          f"{all(all(((i // 5**l) % 5) != 0 for l in range(4)) for i in np.nonzero(nz)[0])}")
    out[f"eq37_{name}"] = dict(norm=float(np.linalg.norm(col)), n_nonzero=int(nz.sum()), amp_min=float(mags.min()), amp_max=float(mags.max()))
out["W_vs_own"] = dict(cg=float(d_cg), paulo=float(d_pa), U_cg_vs_linkspace=float(dU))

# ------------------------------------------------------------------ own Gauss generators on the 625-space
sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
def loc(kind, a):
    M = np.zeros((5, 5), complex)
    T = sig[a] / 2
    M[1:, 1:] = np.kron(-T.T, np.eye(2)) if kind == "L" else np.kron(np.eye(2), T)
    return M
def emb(M, link):  # link 0 least significant
    f = np.array([[1.0 + 0j]])
    for l in range(3, -1, -1):
        f = np.kron(f, M if l == link else np.eye(5))
    return f
# corners: link order b0 r1 t2 l3; links start/end: b:(0,0)->(1,0), r:(1,0)->(1,1), t:(0,1)->(1,1), l:(0,0)->(0,1)
# start of link -> 'L' end, end of link -> 'R' end.
inner_ends = {(0, 0): [(0, "L"), (3, "L")], (1, 0): [(0, "R"), (1, "L")], (1, 1): [(1, "R"), (2, "R")], (0, 1): [(2, "L"), (3, "R")]}
comm = {}
for site, ends in inner_ends.items():
    for a in range(3):
        G = sum(emb(loc(side, a), link) for link, side in ends)
        for name, Wm in (("cg", W_cg_own), ("paulo", W_pa_own)):
            if name == "paulo":
                continue  # Paulo-basis generators differ by V_P; checked via cg basis
            comm[(site, a)] = max(comm.get((site, a), 0), float(np.abs(Wm @ G - G @ Wm).max()))
print(f"(2a) max |[W_own, G_c^a(inner part)]| over 4 corners x 3 colours (625-space, cg) = {max(comm.values()):.2e}")
# negative control: a non-invariant operator, W with one link's U's replaced (b -> only U_00 term)
Wbad = np.zeros((625, 625), complex)
Wbad_T = np.zeros((5,) * 8, complex)
for a in [0]:
    for b, c, d in itertools.product(range(2), repeat=3):
        Ud = np.einsum("dcxy->cdyx", Ucg).conj()
        Wbad_T += np.einsum("ij,kl,mn,op->ikmojlnp", Ud[d, a], Ud[c, d], Ucg[b, c], Ucg[a, b])
Wbad = Wbad_T.reshape(625, 625)
G0 = sum(emb(loc(side, 0), link) for link, side in inner_ends[(0, 0)])
neg = float(np.abs(Wbad @ G0 - G0 @ Wbad).max())
print(f"     negative control (non-traced chain, a fixed): max|[Wbad,G]| = {neg:.2e}  (must be >> 1e-10)")
out["commutator_inner_gauss"] = dict(max=max(comm.values()), negative_control=neg)

# ------------------------------------------------------------------ own Psi contraction, leak, H_B
basis = P.physical_basis(jmax=0.5, convention="cg")
N = basis.dim
print("dim", N)
Wsp = sp.csr_matrix(W_cg_own)
def apply_W(keys, amps, Wm_sp):
    keys = np.asarray(keys, np.int64); inner = keys % 625; outer = keys // 625
    resk, resa = [], []
    for o in np.unique(outer):
        m = outer == o
        v = np.zeros(625, complex); v[inner[m]] = np.asarray(amps)[m]
        w = Wm_sp @ v
        nz = np.nonzero(np.abs(w) > 1e-15)[0]
        resk.append(nz + 625 * int(o)); resa.append(w[nz])
    return np.concatenate(resk), np.concatenate(resa)

Wk, Wa = [], []
for kx, ax in zip(basis.keys, basis.amps):
    k2, a2 = apply_W(kx, ax, Wsp); Wk.append(k2); Wa.append(a2)
allkeys = np.unique(np.concatenate([np.concatenate(basis.keys), np.concatenate(Wk)]))
def colmat(KL, AL):
    rows = np.searchsorted(allkeys, np.concatenate(KL)); cols = np.concatenate([np.full(len(k), c) for c, k in enumerate(KL)])
    return sp.csr_matrix((np.concatenate(AL).astype(complex), (rows, cols)), shape=(len(allkeys), N))
Psi = colmat(basis.keys, basis.amps)
WPsi = colmat(Wk, Wa)
A = (Psi.conj().T @ WPsi).toarray()
resid = WPsi - Psi @ sp.csr_matrix(A)
res_norm = np.sqrt(np.asarray(resid.conj().multiply(resid).sum(axis=0)).real.ravel())
wn = np.sqrt(np.asarray(WPsi.conj().multiply(WPsi).sum(axis=0)).real.ravel())
leak_own_norm = float(res_norm.max())
leak_own_sq = float(np.max(np.abs(wn**2 - np.sum(np.abs(A)**2, axis=0))))
print(f"(2b) own leak: max_k ||W psi_k - Psi Psi^dag W psi_k|| = {leak_own_norm:.2e};  max | ||W psi||^2 - sum|A|^2 | = {leak_own_sq:.2e}")
HB_own = -(A + A.conj().T)
HB, leak_b = O.h_magnetic_phys(basis)
print(f"    builder leak (h_magnetic_phys 2nd return) = {leak_b:.2e}")
print(f"    max|HB_builder - HB_own| = {np.abs(HB - HB_own).max():.2e}")
herm = float(np.abs(HB - HB.conj().T).max())
print(f"    ||H_B - H_B^dag||_max = {herm:.2e}   (own: {np.abs(HB_own - HB_own.conj().T).max():.2e})")
print(f"    column norms ||W psi_k||: min {wn.min():.4f} max {wn.max():.4f}; max imag of H_B {np.abs(HB.imag).max():.2e}")
out["leak"] = dict(builder=float(leak_b), own_residual_norm=leak_own_norm, own_sq=leak_own_sq,
                   hb_builder_vs_own=float(np.abs(HB - HB_own).max()), hb_herm=herm)

# Gauss residual on W psi_k for all states (own generators, 4 corners x 3 colours, full 12 links), via sparse operators on allkeys
# use dict-based application restricted to a stride sample of 60 states
def apply_local(vec, link, M):
    p = 5 ** link; res = {}
    for k, v in vec.items():
        s = (k // p) % 5; base = k - s * p
        col = M[:, s]
        for s2 in np.nonzero(np.abs(col) > 1e-15)[0]:
            res[base + int(s2) * p] = res.get(base + int(s2) * p, 0) + col[s2] * v
    return res
LINKS = [((0, 0), (1, 0)), ((1, 0), (1, 1)), ((0, 1), (1, 1)), ((0, 0), (0, 1)),
         ((-1, 0), (0, 0)), ((0, -1), (0, 0)), ((1, 0), (2, 0)), ((1, -1), (1, 0)),
         ((1, 1), (2, 1)), ((1, 1), (1, 2)), ((-1, 1), (0, 1)), ((0, 1), (0, 2))]
SITES = [(0, 0), (1, 0), (1, 1), (0, 1)]
CORN = [[(i, "L" if a == s else "R") for i, (a, b) in enumerate(LINKS) if a == s or b == s] for s in SITES]
def gauss_w(vec):
    w = 0.0
    for ends in CORN:
        for a in range(3):
            tot = {}
            for link, side in ends:
                for kk, vv in apply_local(vec, link, loc(side, a)).items():
                    tot[kk] = tot.get(kk, 0) + vv
            w = max(w, float(np.sqrt(sum(abs(x) ** 2 for x in tot.values()))))
    return w
t0 = time.time()
samp = list(range(0, N, 5))
gw = max(gauss_w({int(k): complex(a) for k, a in zip(Wk[c], Wa[c])}) for c in samp)
print(f"(2c) Gauss residual of (W (x) 1)psi_k, all 12 links, own generators, {len(samp)} states: max {gw:.2e}  ({time.time()-t0:.1f}s)")
out["gauss_of_W_psi"] = dict(n=len(samp), max=gw)

# ------------------------------------------------------------------ (3) closed sector
CLV = ((0.0,) * 12, (0.0,) * 4)
i0 = basis.index(CLV)
cand = [k for k, lab in enumerate(basis.labels) if all(x == 0.5 for x in lab[0][:4]) and all(x == 0.0 for x in lab[0][4:])]
print("    closed-sector candidates (inner all 1/2, outer 0):", cand, [basis.labels[k][1] for k in cand])
i1 = [k for k in cand if np.abs(A[k, i0]) > 1e-9][0]
Wamp = A[i1, i0]
Wdag_amp = np.conj(A[i0, i1])   # <16|W^dag|0> = conj(<0|W|16>)
print(f"(3) <16|W|0> = {Wamp:.12f}; <16|W^dag|0> = <0|W|16>^* = {Wdag_amp:.12f}; sum -> H_B off-diag = {-(Wamp + Wdag_amp):.12f}")
print(f"    column 0 of A (W psi_0 on physical states): nonzero rows {np.nonzero(np.abs(A[:, i0]) > 1e-12)[0].tolist()}, |A|={np.abs(A[:, i0][np.abs(A[:, i0])>1e-12])}")
print(f"    ||W psi_0||^2 = {wn[i0]**2:.12f} (should be 1 = |<16|W|0>|^2 -> closed under W)")
out["closed"] = dict(W_01=complex(Wamp).__repr__(), Wdag_01=complex(Wdag_amp).__repr__(), norm_W_psi0=float(wn[i0]), rows=np.nonzero(np.abs(A[:, i0]) > 1e-12)[0].tolist())
# 3/2: electric
HEi = O.h_electric_inner(basis)
print(f"    H_E^inner(|0000>)={HEi[i0]}, H_E^inner(|16>)={HEi[i1]}  = 4 links x j(j+1)=3/4 -> 3; times g^2/2 -> 3 g^2/2")
for g2 in (0.5, 1.0, 2.0):
    H = O.hamiltonian_phys(basis, g2)
    blk = H[np.ix_([i0, i1], [i0, i1])]
    exp = np.array([[0, -2 / g2], [-2 / g2, 1.5 * g2]])
    # allow sign gauge: compare with |offdiag|
    d = max(abs(blk[0, 0]), abs(blk[1, 1] - 1.5 * g2), abs(abs(blk[0, 1]) - 2 / g2), abs(abs(blk[1, 0]) - 2 / g2))
    leak_to_others = np.abs(H[np.ix_([i0, i1], [k for k in range(N) if k not in (i0, i1)])]).max()
    # own build
    Hown = np.diag(0.5 * g2 * HEi) + HB_own / g2
    print(f"    g2={g2}: block={np.round(blk.real,12).tolist()} (imag {np.abs(blk.imag).max():.1e}), dev from [[0,-2/g2],[-2/g2,3g2/2]] (mod sign) = {d:.2e}, "
          f"coupling to other 431 states = {leak_to_others:.1e}, own-vs-builder H = {np.abs(Hown - H).max():.1e}")
    ev = np.linalg.eigvalsh(blk)
    out.setdefault("closed_block", {})[str(g2)] = dict(block=blk.real.tolist(), dev=float(d), decoupled=float(leak_to_others),
                                                       eig=ev.tolist(), eig_exact=sorted(np.linalg.eigvalsh(exp).tolist()))

# ------------------------------------------------------------------ (4) spectrum of H_B
def spec(Hm, tag):
    ev = np.linalg.eigvalsh((Hm + Hm.conj().T) / 2)
    vals, counts = [], []
    for e in ev:
        if vals and abs(e - vals[-1]) < 1e-8:
            counts[-1] += 1; vals[-1] = (vals[-1] * (counts[-1] - 1) + e) / counts[-1]
        else:
            vals.append(e); counts.append(1)
    print(f"(4) spectrum H_B^phys ({tag}): {len(vals)} distinct eigenvalues, sum counts {sum(counts)}, trace {ev.sum():.3e}")
    for v, c in zip(vals, counts):
        print(f"      {v:+.10f}  x{c}")
    return vals, counts
vals, counts = spec(HB, "cg")
basis_p = P.physical_basis(jmax=0.5, convention="paulo")
HBp, leak_p = O.h_magnetic_phys(basis_p)
valsp, countsp = spec(HBp, "paulo")
print(f"    paulo vs cg eigenvalue max diff: {np.abs(np.linalg.eigvalsh(HB) - np.linalg.eigvalsh(HBp)).max():.2e}; paulo leak {leak_p:.2e}; paulo herm {np.abs(HBp-HBp.conj().T).max():.2e}")
out["HB_spectrum_cg"] = dict(values=[float(v) for v in vals], mult=counts, trace=float(np.trace(HB).real))
out["HB_spectrum_paulo_leak"] = float(leak_p)

# ------------------------------------------------------------------ (5) targets
def own_targets(a, b, HBm, HEv):
    UE = np.diag(np.exp(-1j * a * HEv)); UB = expm(-1j * b * HBm)
    UEh = np.diag(np.exp(-1j * a / 2 * HEv))
    return UE, UB, UB @ UE, UEh @ UB @ UEh
HEo = O.h_electric_outer(basis)
UE, UB, S1, S2 = own_targets(al, be, HB_own, HEi)
t = lambda **kw: O.target(basis, **kw)
dd = dict(UE=np.abs(t(kind="UE", alpha=al) - UE).max(), UB=np.abs(t(kind="UB", beta=be) - UB).max(),
          S1=np.abs(t(kind="step", alpha=al, beta=be, order=1) - S1).max(), S2=np.abs(t(kind="step", alpha=al, beta=be, order=2) - S2).max())
S1o = t(kind="step", alpha=al, beta=be, order=1, include_outer_electric=True)
S2o = t(kind="step", alpha=al, beta=be, order=2, include_outer_electric=True)
dd["S1_outer"] = np.abs(S1o - UB @ np.diag(np.exp(-1j * al * (HEi + HEo)))).max()
dd["S2_outer"] = np.abs(S2o - np.diag(np.exp(-1j * al / 2 * (HEi + HEo))) @ UB @ np.diag(np.exp(-1j * al / 2 * (HEi + HEo)))).max()
unit = {k: float(np.abs(m.conj().T @ m - np.eye(N)).max()) for k, m in dict(UE=t(kind="UE", alpha=al), UB=t(kind="UB", beta=be),
        S1=t(kind="step", alpha=al, beta=be, order=1), S2=t(kind="step", alpha=al, beta=be, order=2), S1o=S1o, S2o=S2o).items()}
print("(5) targets vs own expm products (max abs):", {k: f"{v:.1e}" for k, v in dd.items()})
print("    unitarity max|U^dag U - 1|:", {k: f"{v:.1e}" for k, v in unit.items()})
dets = {k: abs(np.linalg.det(m)) for k, m in dict(UB=t(kind="UB", beta=be), S2=t(kind="step", alpha=al, beta=be, order=2)).items()}
print("    |det| (should be 1):", dets)
out["targets_vs_own"] = {k: float(v) for k, v in dd.items()}; out["unitarity"] = unit
# order scaling
CM = HB_own @ np.diag(HEi) - np.diag(HEi) @ HB_own
print(f"    ||[H_B,H_E]||_2 = {np.linalg.norm(CM, 2):.6f}")
sc, nrm, pred = [], [], []
for s in (1.0, 0.5, 0.25, 0.125):
    a, b = al * s, be * s
    D1 = t(kind="step", alpha=a, beta=b, order=1); D2 = t(kind="step", alpha=a, beta=b, order=2)
    nrm.append(float(np.linalg.norm(D2 - D1, 2))); sc.append(s); pred.append(0.5 * a * b * np.linalg.norm(CM, 2))
slope_pairs = [np.log(nrm[i] / nrm[i + 1]) / np.log(2) for i in range(len(nrm) - 1)]
slope_fit = float(np.polyfit(np.log(sc), np.log(nrm), 1)[0])
for s, n_, p in zip(sc, nrm, pred):
    print(f"    scale {s:5.3f}: (a,b)=({al*s:.4f},{be*s:.4f})  ||U2-U1||_2 = {n_:.6e}   leading estimate a*b/2*||[HB,HE]|| = {p:.6e}  ratio {n_/p:.4f}")
print(f"    successive slopes log2(err(s)/err(s/2)) = {[round(x,4) for x in slope_pairs]};  fitted log-log slope vs scale = {slope_fit:.4f} (expect 2)")
out["order_scaling"] = dict(scales=sc, norm_U2_minus_U1=nrm, leading_est=[float(x) for x in pred], slopes=[float(x) for x in slope_pairs], fit=slope_fit)
# convergence order of each to the exact exp(-i(aHE+bHB)): errors per scale, expected slope 2 (order 1) and 3 (order 2) for fixed ratio a/b
ex = lambda s: expm(-1j * (al * s * np.diag(HEi) + be * s * HB_own))
e1, e2 = [], []
for s in sc:
    E = ex(s)
    e1.append(float(np.linalg.norm(t(kind="step", alpha=al * s, beta=be * s, order=1) - E, 2)))
    e2.append(float(np.linalg.norm(t(kind="step", alpha=al * s, beta=be * s, order=2) - E, 2)))
print("    local error vs exact exp(-i(aHE+bHB)): order1", [f"{x:.2e}" for x in e1], "slope", round(float(np.polyfit(np.log(sc), np.log(e1), 1)[0]), 3),
      "| order2", [f"{x:.2e}" for x in e2], "slope", round(float(np.polyfit(np.log(sc), np.log(e2), 1)[0]), 3), "(expect 2 and 3)")
out["local_error_vs_exact"] = dict(order1=e1, order2=e2, slope1=float(np.polyfit(np.log(sc), np.log(e1), 1)[0]), slope2=float(np.polyfit(np.log(sc), np.log(e2), 1)[0]))
# composition group property
dgrp = np.abs(t(kind="UB", beta=0.25) @ t(kind="UB", beta=0.36) - UB).max()
print(f"    UB(0.25)UB(0.36)-UB(0.61) = {dgrp:.1e}")
out["UB_group"] = float(dgrp)

json.dump(out, open("results/tester_m0_step05_operators.json", "w"), indent=1, default=str)
print("saved results/tester_m0_step05_operators.json")
