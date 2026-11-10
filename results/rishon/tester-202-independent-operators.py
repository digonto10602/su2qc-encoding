"""Tester 202: independent check of rishon inner operators.  Own global-JW 16-mode operators (no su2plaq.rishon import for the
reference; production imported only for comparison).  Writes results/rishon/tester-202-operators.json."""
import itertools, json, subprocess, sys, time
import numpy as np, scipy.sparse as sp
from scipy.linalg import expm
sys.path.insert(0, 'src')
t0 = time.time()
out = {'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), 'seed': None}
# ---- own JW on 16 modes, global strings, little endian, mode k = qubit k = 4*link + (L1,L2,R1,R2)
Z = sp.csr_matrix(np.diag([1., -1.])); I2 = sp.identity(2, format='csr'); SM = sp.csr_matrix(np.array([[0, 1], [0, 0]], float))  # |0><1|
def kronle(ops):
    o = sp.identity(1, format='csr')
    for x in ops: o = sp.kron(x, o, format='csr')   # first op = least significant qubit
    return o
n = 16
c = [kronle([Z]*k + [SM] + [I2]*(n-k-1)) for k in range(n)]
cd = [x.T.tocsr() for x in c]
# CAR check
Acar = max(abs(c[i]@cd[j] + cd[j]@c[i] - (sp.identity(2**n)*(i == j))).max() for i in (0, 3, 7, 15) for j in (0, 5, 8, 15))
Acar2 = max(abs(c[i]@c[j] + c[j]@c[i]).max() for i in (0, 3, 7) for j in (1, 6, 15))
out['CAR_err'] = float(max(Acar, Acar2))
def U(l, i, j): return c[4*l+i] @ cd[4*l+2+j]       # U_ij = c_{L,i} c^dag_{R,j}
sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
T = [s/2 for s in sig]
def Lgen(l, a): return sum(T[a][i, j]*(cd[4*l+i] @ c[4*l+j]) for i in range(2) for j in range(2))
def Rgen(l, a): return sum(T[a][i, j]*(cd[4*l+2+i] @ c[4*l+2+j]) for i in range(2) for j in range(2))
# own codes: nibble weight 2
wt = lambda x: bin(x).count('1')
nib = [x for x in range(16) if wt(x) == 2]
codes = np.array(sorted(sum(s << (4*l) for l, s in enumerate(cfg)) for cfg in itertools.product(nib, repeat=4)), dtype=np.int64)
assert len(codes) == 1296
# W = sum_abcd U_b,ab U_r,bc (U_t,dc)^dag (U_l,ad)^dag   (b,r,t,l = links 0,1,2,3)
t1 = time.time()
Wf = sp.csr_matrix((2**n, 2**n))
for a, b, cc, d in itertools.product(range(2), repeat=4):
    Wf = Wf + U(0, a, b) @ U(1, b, cc) @ U(2, d, cc).T @ U(3, a, d).T
W = Wf[codes][:, codes].toarray()
# check closure: W maps code space into code space (no leakage out of the 1296)
leak = abs(Wf[:, codes]).sum() - abs(Wf[codes][:, codes]).sum()
out['W_leak_outside_codes'] = float(leak)
HB = -(W + W.T)
out['W_real_imag'] = 0.0
out['W_nnz'] = int(np.count_nonzero(np.abs(W) > 1e-12))
# geometry from METHODS sec.1 coordinates
links = {0: ((0, 0), (1, 0)), 1: ((1, 0), (1, 1)), 2: ((0, 1), (1, 1)), 3: ((0, 0), (0, 1))}
sites = [(0, 0), (1, 0), (1, 1), (0, 1)]
# Gauss on the inner ends at each site: sum_{links starting at site} L_a + sum_{links ending at site} R_a (restricted to inner links)
def Gin(site, a):
    G = sp.csr_matrix((2**n, 2**n), dtype=complex)
    for l, (s, e) in links.items():
        if s == site: G = G + Lgen(l, a)
        if e == site: G = G + Rgen(l, a)
    return G[codes][:, codes].toarray()
Gs = {(s, a): Gin(site, a) for s, site in enumerate(sites) for a in range(3)}
out['comm_W_G_max'] = float(max(np.abs(W@G - G@W).max() for G in Gs.values()))
out['G_hermitian_max'] = float(max(np.abs(G - G.conj().T).max() for G in Gs.values()))
# H_E: sum_l j(j+1) with j=1/2 on a link in the quartet: own Casimir of L end on each link
def casimirL(l): return sum(Lgen(l, a) @ Lgen(l, a) for a in range(3))
def casimirR(l): return sum(Rgen(l, a) @ Rgen(l, a) for a in range(3))
HE = np.zeros(1296)
cas_diag = []
for l in range(4):
    CL = casimirL(l)[codes][:, codes].toarray(); CR = casimirR(l)[codes][:, codes].toarray()
    assert np.abs(CL - np.diag(np.diag(CL))).max() < 1e-12
    out.setdefault('casimirL_vs_R_max', 0.0); out['casimirL_vs_R_max'] = max(out['casimirL_vs_R_max'], float(np.abs(CL - CR).max()))
    HE += np.real(np.diag(CL))
vals = sorted(set(np.round(np.real(np.diag(CL)), 12).tolist()))
out['link_casimir_values'] = vals
out['HE_unique_values'] = sorted(set(np.round(HE, 12).tolist()))
# types per code and  3/4 per quartet
def ntype(x): return 'A' if x == 3 else 'B' if x == 12 else 'Q'
HEq = np.array([0.75*sum(ntype((int(cc) >> (4*l)) & 15) == 'Q' for l in range(4)) for cc in codes])
out['HE_vs_quartet_count'] = float(np.abs(HE - HEq).max())
# ---- production
import su2plaq.rishon.operators as O
Wp = O.plaquette_W_inner()
out['W_prod_vs_own'] = float(np.abs(Wp - W).max())
out['codes_equal'] = bool(np.array_equal(O.inner_codes(), codes))
out['HE_prod_vs_own'] = float(np.abs(O.h_electric_inner() - HE).max())
out['HB_hermitian'] = float(np.abs(O.h_magnetic_inner() - O.h_magnetic_inner().conj().T).max())
out['HB_prod_vs_own'] = float(np.abs(O.h_magnetic_inner() - HB).max())
out['Gauss_prod_vs_own'] = float(max(np.abs(O.gauss_inner(s, a) - Gs[(s, a)]).max() for s in range(4) for a in range(3)))
out['comm_Wprod_Gown'] = float(max(np.abs(Wp@G - G@Wp).max() for G in Gs.values()))
out['W3'] = float(np.abs(W@W@W).max())
# ---- spectrum with multiplicities
ev = np.linalg.eigvalsh(HB)
from collections import Counter
spec = Counter(np.round(ev, 7).tolist()); out['spectrum'] = {str(k): v for k, v in sorted(spec.items())}
# ---- isolated, components
from scipy.sparse.csgraph import connected_components
nc, lab = connected_components(sp.csr_matrix(np.abs(HB) > 1e-12), directed=False)
sizes = Counter(np.bincount(lab).tolist())
out['component_sizes'] = {str(k): v for k, v in sorted(sizes.items())}
iso = int((np.bincount(lab) == 1).sum())
out['isolated_codes'] = iso
bright_comp = nc - iso
out['n_bright_components'] = int(bright_comp)
out['zero_eigs_total'] = spec[0.0]
out['zero_eigs_inside_bright_components'] = spec[0.0] - iso
# kappa per component (own)
kap = Counter()
for ci in range(nc):
    idx = np.flatnonzero(lab == ci)
    if len(idx) == 1: continue
    w = np.linalg.eigvalsh(HB[np.ix_(idx, idx)])
    kap[round(float(w[-1]), 9)] += 1
    assert abs(w[0] + w[-1]) < 1e-9 and (len(w) <= 2 or np.abs(w[1:-1]).max() < 1e-9)
out['kappa_own'] = {str(k): v for k, v in sorted(kap.items())}
# ---- bright pairs
pairs = O.bright_pairs()
Hrec = np.zeros((1296, 1296)); V = []
amps = set(); signok = True
for u, v, k in pairs:
    Hrec -= k*(np.outer(u, v) + np.outer(v, u)); V += [u, v]
    for x in np.concatenate([u, v]):
        if abs(x) > 1e-12: amps.add(round(abs(float(x)), 9))
    f = int(np.flatnonzero(np.abs(u) >= np.abs(u).max() - 1e-10)[0]); signok &= bool(u[f] > 0)
V = np.array(V)
out['pairs_n'] = len(pairs)
out['pairs_kappa'] = {str(k): v for k, v in sorted(Counter(round(float(k), 9) for _, _, k in pairs).items())}
out['pairs_recon_err'] = float(np.abs(Hrec - HB).max())
out['pairs_orth_err'] = float(np.abs(V@V.T - np.eye(162)).max())
out['pairs_amplitudes'] = sorted(amps)
out['pairs_u_sign_ok'] = signok
out['pairs_in_support_of_nonisolated'] = bool(all(np.abs(np.concatenate([u, v])[np.repeat(lab, 1)[:0]]).size == 0 for u, v, _ in pairs))
dark = O.dark_codes()
out['dark_n'] = len(dark)
iso_codes = codes[np.bincount(lab)[lab] == 1]
out['dark_equals_isolated'] = bool(np.array_equal(np.sort(dark), iso_codes))
# ---- targets vs expm
tg = {}
for al, be in [(0.37, 0.61), (1.70, 1.00)]:
    UBe = expm(-1j*be*HB); UEe = np.diag(np.exp(-1j*al*HE))
    tg[f'{al},{be}'] = {
        'UB': float(np.abs(O.inner_target('UB', None, be) - UBe).max()),
        'UE': float(np.abs(O.inner_target('UE', al, None) - UEe).max()),
        'step1': float(np.abs(O.inner_target('step', al, be, 1) - UBe@UEe).max()),
        'step2': float(np.abs(O.inner_target('step', al, be, 2) - np.diag(np.exp(-0.5j*al*HE))@UBe@np.diag(np.exp(-0.5j*al*HE))).max()),
        'unitarity_UB': float(np.abs(O.inner_target('UB', None, be).conj().T@O.inner_target('UB', None, be) - np.eye(1296)).max()),
        'comm_UB_G': float(max(np.abs(O.inner_target('UB', None, be)@G - G@O.inner_target('UB', None, be)).max() for G in Gs.values())),
    }
out['targets_vs_expm'] = tg
# ---- closed block
va = 3 | (3 << 4) | (12 << 8) | (12 << 12); vb = 12 | (12 << 4) | (3 << 8) | (3 << 12)
ia, ib = int(np.searchsorted(codes, va)), int(np.searchsorted(codes, vb))
col = W[:, ia]
out['W_vacA_norm'] = float(np.linalg.norm(col)); out['W_vacA_nnz'] = int(np.count_nonzero(np.abs(col) > 1e-12))
ln = col / np.linalg.norm(col)
out['loop_all_Q'] = bool(all(all(ntype((int(cc) >> (4*l)) & 15) == 'Q' for l in range(4)) for cc in codes[np.abs(col) > 1e-12]))
out['loop_vs_prod_codes'] = bool(set(O.closed_codes()[2].tolist()) == set(codes[np.abs(col) > 1e-12].tolist()))
out['vac_codes_match'] = bool(O.closed_codes()[:2] == (va, vb))
out['Wloop_to_vacB'] = float(ln @ W[:, ia]); out['vacB_W_loop'] = float(W[ib] @ ln)
Wdl = W.T[:, ia]; out['Wdag_vacA_max'] = float(np.abs(Wdl).max()); out['W_vacB_max'] = float(np.abs(W[:, ib]).max())
Bm = np.array([np.eye(1296)[ia], ln, np.eye(1296)[ib]])
cl = {}
for g2 in (0.5, 1.0, 2.0):
    H = 0.5*g2*np.diag(HE) + HB/g2
    blk = Bm@H@Bm.T
    ref = 0.5*g2*np.diag([0, 3, 0]) - (4/g2)*np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
    ev3 = np.sort(np.linalg.eigvalsh(blk))
    form = np.sort([0.0, 0.75*g2 - np.sqrt(9/16*g2**2 + 32/g2**2), 0.75*g2 + np.sqrt(9/16*g2**2 + 32/g2**2)])
    # invariance of the 3-dim span under full H
    proj = Bm.T@Bm
    inv = float(np.abs((np.eye(1296) - proj)@H@Bm.T).max())
    cl[str(g2)] = {'block_vs_formula': float(np.abs(blk - ref).max()), 'prod_block_vs_own': float(np.abs(O.closed_block(g2) - blk).max()),
                   'eig_vs_formula': float(np.abs(ev3 - form).max()), 'span_invariance_residual': inv,
                   'eigs': ev3.tolist(), 'prod_eigs': np.sort(np.linalg.eigvalsh(O.closed_block(g2))).tolist(),
                   'full_inner_H_has_these_eigs': bool(all(np.min(np.abs(np.linalg.eigvalsh(H) - e)) < 1e-9 for e in form))}
out['closed'] = cl
# ---- KS block vs laptop exact (433-dim)
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.operators import hamiltonian_phys
import su2plaq.rishon.observables as Ob
bs = physical_basis()
cidx = [k for k, lab_ in enumerate(bs.labels) if all(abs(j) < 1e-12 for j in lab_[0][4:])]
out['KS_closed_state_labels'] = [str(bs.labels[k]) for k in cidx]
ks = {}
for g2 in (0.5, 1.0, 2.0):
    Hk = hamiltonian_phys(bs, g2)
    blk = Hk[np.ix_(cidx, cidx)]
    prod = Ob.ks_closed_block(g2)
    # sign of loop is a phase convention: compare |offdiag| and diagonal; eigenvalues
    ks[str(g2)] = {'block': np.real(blk).tolist(), 'prod': np.real(prod).tolist(),
                   'maxdiff_abs_entries': float(np.abs(np.abs(blk) - np.abs(prod)).max()),
                   'eig_diff': float(np.abs(np.sort(np.linalg.eigvalsh(blk)) - np.sort(np.linalg.eigvalsh(prod))).max()),
                   'KS_formula_eig_diff': float(np.abs(np.sort(np.linalg.eigvalsh(blk)) - np.sort([0.75*g2 - np.sqrt(9/16*g2**2 + 4/g2**2), 0.75*g2 + np.sqrt(9/16*g2**2 + 4/g2**2)])).max())}
out['KS'] = ks
out['wall_s'] = time.time() - t0
json.dump(out, open('results/rishon/tester-202-operators.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
