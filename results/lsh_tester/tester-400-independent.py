"""Tester-400 independent check of the LSH plaquette model (steps 7.0-7.2).
Own implementation from the Raychowdhury-Stryker (arXiv:1912.06133) definitions: Schwinger-boson Fock space of one
trivalent site, loop states, link-end operators U_L, U_R, plaquette trace.  Project code used ONLY as the comparison
reference: exact.spinnet (route B), exact.physical/operators/compare (route A), and, at the end, lsh.operators for comparison.
No code of src/su2plaq/lsh builds the independent numbers.  Deterministic (no RNG).
Run: PYTHONPATH=src python results/lsh_tester/tester-400-independent.py
"""
import itertools, json, math, sys, subprocess
import numpy as np
import scipy.sparse as sp

out = {}
# ------------------------------------------------------------------ (a) site rules from spins
def triangle(a, b, c):
    return abs(a - b) <= c + 1e-12 and c <= a + b + 1e-12 and abs((a + b + c) - round(a + b + c)) < 1e-12

valid_codes = []
sites = {}
for j1 in (0, .5):
    for j2 in (0, .5):
        for J in (0, .5, 1):
            if triangle(j1, j2, J):
                l12, l23, l31 = j1 + j2 - J, j2 + J - j1, J + j1 - j2
                code = int(round(l12)) + 2 * int(round(l23)) + 4 * int(round(l31))
                valid_codes.append(code); sites[code] = (j1, j2, J)
valid_codes = sorted(valid_codes)
print("valid site codes from triangle rule with j<=1/2 legs 1,2 and J<=1:", valid_codes, sites)
out["valid_site_codes"] = valid_codes
assert valid_codes == [0, 1, 2, 4, 6]

def flux(s):  # (N1, N2, N3)
    l12, l23, l31 = s & 1, s >> 1 & 1, s >> 2 & 1
    return (l31 + l12, l12 + l23, l23 + l31)

# ------------------------------------------------------------------ (b) brute force 5^8 and raw 2^24
V = valid_codes
cnt = 0; inner_set = set()
for ss in itertools.product(V, repeat=8):
    fl = [flux(s) for s in ss]
    ok = True
    for c in range(4):
        if fl[c][1] != fl[(c + 1) % 4][0]: ok = False; break   # inner link AGL
        if fl[c][2] != fl[4 + c][2]: ok = False; break          # virtual link AGL
    if ok:
        cnt += 1
        inner_set.add(ss[:4])
print("brute 5^8 -> physical:", cnt, " inner codes:", len(inner_set))
out["n_physical_5^8"] = cnt; out["n_inner"] = len(inner_set)
assert cnt == 433 and len(inner_set) == 47

x = np.arange(1 << 24, dtype=np.int64)
sc = [((x >> (3 * k)) & 7).astype(np.int8) for k in range(8)]
l12 = [s & 1 for s in sc]; l23 = [(s >> 1) & 1 for s in sc]; l31 = [(s >> 2) & 1 for s in sc]
N1 = [l31[k] + l12[k] for k in range(8)]; N2 = [l12[k] + l23[k] for k in range(8)]; N3 = [l23[k] + l31[k] for k in range(8)]
agl = np.ones(1 << 24, bool)
for c in range(4):
    agl &= (N2[c] == N1[(c + 1) % 4]) & (N3[c] == N3[4 + c])
cap = np.ones(1 << 24, bool)
for k in range(8):
    cap &= (N1[k] <= 1) & (N2[k] <= 1)
print("2^24: AGL only", int(agl.sum()), " AGL+cap", int((agl & cap).sum()))
out["raw_AGL_only"] = int(agl.sum()); out["raw_AGL_cap"] = int((agl & cap).sum())
assert int((agl & cap).sum()) == 433 and int(agl.sum()) == 5920
y = np.arange(1 << 12)
s4 = [(y >> (3 * k)) & 7 for k in range(4)]
f1 = [((s >> 2 & 1) + (s & 1)) for s in s4]; f2 = [((s & 1) + (s >> 1 & 1)) for s in s4]
inner_agl = np.ones(1 << 12, bool)
for c in range(4): inner_agl &= f2[c] == f1[(c + 1) % 4]
print("12-bit inner AGL only:", int(inner_agl.sum()))
out["raw_inner_AGL_only"] = int(inner_agl.sum())
phys = x[agl & cap]
print("distinct outer 12-bit patterns among the 433:", len(set((phys >> 12).tolist())))
out["n_outer_patterns"] = len(set((phys >> 12).tolist()))
del x, sc, l12, l23, l31, N1, N2, N3, agl, cap

# ------------------------------------------------------------------ (c) Fock-space plaquette
NMAX = 4
NM = 6
dim = (NMAX + 1) ** NM
a1 = sp.csr_matrix(np.diag(np.sqrt(np.arange(1, NMAX + 1)), 1))
I1 = sp.identity(NMAX + 1, format="csr")
def mode(m):
    o = None
    for q in range(NM):
        f = a1 if q == m else I1
        o = f if o is None else sp.kron(o, f, format="csr")
    return o
A = [mode(m) for m in range(NM)]          # mode index = 2*leg + alpha
Ad = [m.T.tocsr() for m in A]
def a(leg, al): return A[2 * leg + al]
def ad(leg, al): return Ad[2 * leg + al]
def Nop(leg): return ad(leg, 0) @ a(leg, 0) + ad(leg, 1) @ a(leg, 1)
def inv_sqrt_Np1(leg):
    d = Nop(leg).diagonal()
    return sp.diags(1.0 / np.sqrt(d + 1.0), format="csr")
Zero = sp.csr_matrix((dim, dim))
def UL(leg):
    n = inv_sqrt_Np1(leg)
    return [[n @ ad(leg, 1), n @ a(leg, 0)], [-(n @ ad(leg, 0)), n @ a(leg, 1)]]
def UR(leg):
    n = inv_sqrt_Np1(leg)
    return [[ad(leg, 0) @ n, ad(leg, 1) @ n], [-(a(leg, 1) @ n), a(leg, 0) @ n]]
def dag(M):   # (X^dagger)_{ij} = (X_{ji})^dagger
    return [[M[j][i].T.conj().tocsr() for j in range(2)] for i in range(2)]
def mprod(M1, M2):
    return [[sum((M1[i][m] @ M2[m][k] for m in range(2)), Zero) for k in range(2)] for i in range(2)]

def Lpp(i, j):
    return ad(i, 0) @ ad(j, 1) - ad(i, 1) @ ad(j, 0)
vac = np.zeros(dim); vac[0] = 1.0
def loop_state(l12, l23, l31):
    v = vac.copy()
    for (i, j), n in (((0, 1), l12), ((1, 2), l23), ((2, 0), l31)):
        for _ in range(n): v = Lpp(i, j) @ v
    S = l12 + l23 + l31
    return v / math.sqrt(math.factorial(l12) * math.factorial(l23) * math.factorial(l31) * math.factorial(S + 1))
ls = {s: loop_state(s & 1, s >> 1 & 1, s >> 2 & 1) for s in range(8)}
G = np.array([[ls[s] @ ls[t] for t in range(8)] for s in range(8)])
print("loop-state Gram - 1:", np.abs(G - np.eye(8)).max())
for s in range(8):
    for leg in range(3):
        assert np.linalg.norm(Nop(leg) @ ls[s] - flux(s)[leg] * ls[s]) < 1e-12, (s, leg)
out["fock_gram_err"] = float(np.abs(G - np.eye(8)).max())

# end operators per corner c (legs: p = 0, n = 1, v = 2); trace order  U_b U_r U_t^dag U_l^dag, U = U_L U_R
ends = {
    0: (dag(UL(0)), UL(1)),       # l (L end, dagger) | b (L end)
    1: (UR(0), UL(1)),            # b R end | r L end
    2: (UR(0), dag(UR(1))),       # r R end | t R end dagger
    3: (dag(UL(0)), dag(UR(1))),  # t L end dagger | l R end dagger
}
Vc = {c: mprod(*ends[c]) for c in range(4)}
E = np.zeros((4, 2, 2, 8, 8))
for c in range(4):
    for i in range(2):
        for k in range(2):
            Mv = Vc[c][i][k]
            for sold in range(8):
                w = Mv @ ls[sold]
                for snew in range(8):
                    E[c, i, k, snew, sold] = ls[snew] @ w
inner = sorted(sum(s << (3 * c) for c, s in enumerate(ss)) for ss in inner_set)
pos = {c: i for i, c in enumerate(inner)}
P = np.zeros((47, 47))
for col, code in enumerate(inner):
    so = [(code >> (3 * c)) & 7 for c in range(4)]
    for idx in itertools.product(range(2), repeat=4):   # tr(V0 V1 V2 V3), V_c[i_c, i_{c+1}]
        pairs = [(idx[c], idx[(c + 1) % 4]) for c in range(4)]
        for newc in inner:
            sn = [(newc >> (3 * c)) & 7 for c in range(4)]
            amp = 1.0
            for c in range(4):
                amp *= E[c, pairs[c][0], pairs[c][1], sn[c], so[c]]
                if amp == 0: break
            if amp != 0: P[pos[newc], col] += amp
print("P nnz", int((np.abs(P) > 1e-12).sum()), " symmetric err", np.abs(P - P.T).max())
K_ind = -(P + P.T)
out["P_nnz"] = int((np.abs(P) > 1e-12).sum())
col_nz = (np.abs(K_ind).max(axis=0) > 1e-12)
print("bright", int(col_nz.sum()), "dark", int((~col_nz).sum()))
out["bright"] = int(col_nz.sum()); out["dark"] = int((~col_nz).sum())
dark_expected = [any(((c >> (3 * k)) & 7) == 6 for k in range(4)) for c in inner]
assert list(~col_nz) == dark_expected
vals = sorted(np.round(K_ind[np.abs(K_ind) > 1e-12], 9).tolist())
out["K_coupling_counts"] = {str(v): vals.count(v) for v in sorted(set(vals))}
print("K nonzero values (count):", out["K_coupling_counts"])

# ------------------------------------------------------------------ (d) compare with route B and route A
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.exact import spinnet as SN
il = SN.inner_labels(jmax=0.5)
PN = [(3, 0), (0, 1), (1, 2), (2, 3)]
def site_code_of(j1, j2, j3):
    l12, l23, l31 = j1 + j2 - j3, j2 + j3 - j1, j3 + j1 - j2
    return int(round(l12)) + 2 * int(round(l23)) + 4 * int(round(l31))
def inner_code_from_label(j4, J):
    return sum(site_code_of(j4[p], j4[n], J[c]) << (3 * c) for c, (p, n) in enumerate(PN))
il_codes = [inner_code_from_label(j, J) for j, J in il]
assert sorted(il_codes) == inner
perm = [il_codes.index(c) for c in inner]
K6 = SN.K_inner(jmax=0.5)[np.ix_(perm, perm)]
d_ind_6j = float(np.abs(K_ind - K6).max())
print("max|K_indep(Fock) - K_6j| =", d_ind_6j)
out["max_K_indep_minus_6j"] = d_ind_6j

from su2plaq.lsh import operators as O
assert O.inner_codes().tolist() == inner
Kp = O.K_lsh()
out["max_K_project_minus_6j"] = float(np.abs(Kp - K6).max()); out["max_K_project_minus_indep"] = float(np.abs(Kp - K_ind).max())
out["max_P_proj_minus_indep"] = float(np.abs(O.plaquette_inner() - P).max())
print("max|K_LSH(project) - K_6j| =", out["max_K_project_minus_6j"], "  max|K_LSH(project) - K_indep| =", out["max_K_project_minus_indep"],
      "  max|P_proj - P_indep| =", out["max_P_proj_minus_indep"])
assert O.physical_codes().tolist() == sorted(phys.tolist())
print("project physical_codes == my 2^24 filter: True")

labels = SN.labels(jmax=0.5)
def code_of_label(lab):
    j, J = lab
    code = inner_code_from_label(j[:4], J)
    for c, (o1, o2) in enumerate([(4, 5), (6, 7), (8, 9), (10, 11)]):
        code |= site_code_of(j[o1], j[o2], J[c]) << (12 + 3 * c)
    return code
full = [code_of_label(l) for l in labels]
assert len(set(full)) == 433 and sorted(full) == sorted(phys.tolist())
print("433 labels map injectively onto the brute-force physical codes: True")
inner_pos = {c: i for i, c in enumerate(inner)}
n = 433
HB = np.zeros((n, n))
for r, cr in enumerate(full):
    for c_, cc in enumerate(full):
        if (cr >> 12) == (cc >> 12):
            HB[r, c_] = K_ind[inner_pos[cr & 0xFFF], inner_pos[cc & 0xFFF]]
def HE_of(code, outer=False):
    s = [(code >> (3 * k)) & 7 for k in range(8)]
    e = sum((flux(s[c])[1] / 2) * (flux(s[c])[1] / 2 + 1) for c in range(4))
    if outer:
        e += sum((f / 2) * (f / 2 + 1) for c in range(4) for f in flux(s[4 + c])[:2])
    return e
HE = np.array([HE_of(c) for c in full]); HEo = np.array([HE_of(c, True) for c in full])
HB6 = SN.h_magnetic_phys_6j(labels); HE6 = np.diag(SN.h_electric_6j(labels))
HE6o = np.diag(SN.h_electric_6j(labels, inner_only=False))
out["HB_indep_minus_6j"] = float(np.abs(HB - HB6).max())
out["HE_indep_minus_6j_inner"] = float(np.abs(HE - HE6).max()); out["HE_indep_minus_6j_all"] = float(np.abs(HEo - HE6o).max())
print("433x433: |HB_indep - HB_6j| =", out["HB_indep_minus_6j"], " |HE_indep - HE_6j| inner/all =", out["HE_indep_minus_6j_inner"], out["HE_indep_minus_6j_all"])
from collections import Counter
out["HE_inner_hist"] = {str(k): v for k, v in sorted(Counter(np.round(HE, 9).tolist()).items())}
out["HE_all_hist"] = {str(k): v for k, v in sorted(Counter(np.round(HEo, 9).tolist()).items())}
print("H_E (inner links) value: multiplicity", out["HE_inner_hist"])
print("H_E (all 12 links) value: multiplicity", out["HE_all_hist"])
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.operators import h_magnetic_phys, h_electric_inner
from su2plaq.exact.compare import gauge_align
basis = physical_basis(convention="cg")
assert basis.labels == labels
HA, leak = h_magnetic_phys(basis)
HEA = h_electric_inner(basis)
D, res = gauge_align(HA, HB)
print("gauge_align(H_A, HB_indep): residual", res, "  minus signs:", int((np.diag(D).real < 0).sum()) if D is not None else None)
out["gauge_align_residual_indep"] = float(res)
out["gauge_minus_signs"] = int((np.diag(D).real < 0).sum()) if D is not None else None
spec = {}
for g2 in (0.5, 1.0, 2.0):
    def mk(he, hb):
        he = np.asarray(he); hb = np.asarray(hb)
        if he.ndim == 1: he = np.diag(he)
        return 0.5 * g2 * he + hb / g2
    eL = np.linalg.eigvalsh(mk(HE, HB))
    eA = np.linalg.eigvalsh(mk(HEA, HA))
    eB = np.linalg.eigvalsh(mk(HE6, HB6))
    spec[str(g2)] = dict(indepLSH_vs_A=float(np.abs(eL - eA).max()), indepLSH_vs_B=float(np.abs(eL - eB).max()), A_vs_B=float(np.abs(eA - eB).max()),
                         emin=float(eL[0]), emax=float(eL[-1]))
    print("g^2", g2, spec[str(g2)])
out["spectra_independent"] = spec
codes = full
HBp = O.h_magnetic_lsh(codes); HEp = O.h_electric_lsh(codes)
specp = {}
for g2 in (0.5, 1.0, 2.0):
    eP = np.linalg.eigvalsh(0.5 * g2 * np.diag(HEp) + HBp / g2)
    eA = np.linalg.eigvalsh(0.5 * g2 * np.asarray(HEA) + HA / g2) if np.asarray(HEA).ndim == 2 else np.linalg.eigvalsh(0.5 * g2 * np.diag(HEA) + HA / g2)
    eB = np.linalg.eigvalsh(0.5 * g2 * np.diag(HE6) + HB6 / g2)
    specp[str(g2)] = dict(project_vs_A=float(np.abs(eP - eA).max()), project_vs_B=float(np.abs(eP - eB).max()))
    print("project LSH operators, g^2", g2, specp[str(g2)])
out["spectra_project"] = specp
out["HB_project_minus_6j"] = float(np.abs(HBp - HB6).max())
out["HE_project_minus_indep_inner"] = float(np.abs(HEp - HE).max())
out["HE_project_minus_indep_all"] = float(np.abs(O.h_electric_lsh(codes, include_outer=True) - HEo).max())
print("project: |HB - HB_6j| =", out["HB_project_minus_6j"], " |HE - HE_indep| inner/all =", out["HE_project_minus_indep_inner"], out["HE_project_minus_indep_all"])
vals, mult = np.unique(np.round(np.linalg.eigvalsh(HB), 9), return_counts=True)
out["HB_spectrum"] = {str(v): int(m) for v, m in zip(vals, mult)}
print("H_B spectrum (value: multiplicity):", out["HB_spectrum"])
ks = [k for k, c in enumerate(full) if c >> 12 == 0]
o_ = np.argsort([full[k] for k in ks]); ks = [ks[i] for i in o_]
print("closed sector codes", [full[k] for k in ks])
out["closed_block_err"] = {}
for g2 in (0.5, 1.0, 2.0):
    Hm = 0.5 * g2 * np.diag(HE) + HB / g2
    blk = Hm[np.ix_(ks, ks)]
    ref = np.array([[0.0, -2 / g2], [-2 / g2, 1.5 * g2]])
    out["closed_block_err"][str(g2)] = float(np.abs(blk - ref).max())
print("closed block err vs [[0,-2/g2],[-2/g2,3g2/2]]:", out["closed_block_err"])
out["commit"] = subprocess.run(["git", "-C", "/home/digimonk/Projects/su2qc-encoding", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
out["note"] = "tester-400 independent check of LSH steps 7.0-7.2 (deterministic; no RNG); working tree has uncommitted builder files"
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/lsh_tester/tester-400-independent.json", "w"), indent=1)
print("saved")
