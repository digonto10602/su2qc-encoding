"""Tester 208: independent 17-state closed block of the rishon model (own global-JW operators, taken from the tester-202
construction), compared with production closed_block_full / closed_spectra and the committed results/rishon/observables.json.
Seeds: none (deterministic).  Writes results/rishon/tester-208-closed-block.json."""
import itertools, json, subprocess, sys, time
import numpy as np, scipy.sparse as sp
sys.path.insert(0, 'src')
out = {'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), 'seed': None}
Z = sp.csr_matrix(np.diag([1., -1.])); I2 = sp.identity(2, format='csr'); SM = sp.csr_matrix(np.array([[0, 1], [0, 0]], float))
def kronle(ops):
    o = sp.identity(1, format='csr')
    for x in ops: o = sp.kron(x, o, format='csr')
    return o
n = 16
c = [kronle([Z]*k + [SM] + [I2]*(n-k-1)) for k in range(n)]
cd = [x.T.tocsr() for x in c]
def U(l, i, j): return c[4*l+i] @ cd[4*l+2+j]
wt = lambda x: bin(x).count('1')
nib = [x for x in range(16) if wt(x) == 2]
codes = np.array(sorted(sum(s << (4*l) for l, s in enumerate(cfg)) for cfg in itertools.product(nib, repeat=4)), dtype=np.int64)
Wf = sp.csr_matrix((2**n, 2**n))
for a, b, cc, d in itertools.product(range(2), repeat=4):
    Wf = Wf + U(0, a, b) @ U(1, b, cc) @ U(2, d, cc).T @ U(3, a, d).T
W = Wf[codes][:, codes].toarray()
HB = -(W + W.T)
A, B = 3, 12            # type A = nibble 0b0011, type B = nibble 0b1100 (links with all rishons on one end)
def ntype(x): return 'A' if x == A else 'B' if x == B else 'Q'
HE = np.array([0.75*sum(ntype((int(cc) >> (4*l)) & 15) == 'Q' for l in range(4)) for cc in codes])
# 16 vacuum codes: every link in A or B
vac = [sum((A if (k >> l) & 1 == 0 else B) << (4*l) for l in range(4)) for k in range(16)]
vi = [int(np.searchsorted(codes, v)) for v in vac]
assert all(codes[i] == v for i, v in zip(vi, vac)) and len(set(vi)) == 16
out['n_vac_codes'] = len(vi)
# independent check: these are exactly the codes with HE == 0, i.e. no quartet link
zero_codes = np.flatnonzero(HE == 0)
out['codes_with_HE_zero'] = int(len(zero_codes)); out['HE_zero_equals_vac'] = bool(set(zero_codes.tolist()) == set(vi))
# loop state = W|vacA> normalised
va = A | (A << 4) | (B << 8) | (B << 12); vb = B | (B << 4) | (A << 8) | (A << 12)
ia, ib = int(np.searchsorted(codes, va)), int(np.searchsorted(codes, vb))
col = W[:, ia]; nrm = np.linalg.norm(col); loop = col/nrm
out['loop_norm_before'] = float(nrm); out['loop_support'] = int(np.count_nonzero(np.abs(loop) > 1e-12))
out['loop_overlap_with_vac'] = float(np.abs(loop[vi]).max())
# W|vac_k>, W^dag|vac_k> for each of the 16
rows = []
for k, i in enumerate(vi):
    rows.append({'k': k, 'W_norm': float(np.linalg.norm(W[:, i])), 'Wdag_norm': float(np.linalg.norm(W.T[:, i])),
                 'W_overlap_loop': float(loop @ W[:, i]), 'Wdag_overlap_loop': float(loop @ W.T[:, i])})
out['W_on_vac'] = rows
Bm = np.zeros((17, 1296))
for r, i in enumerate(vi): Bm[r, i] = 1
Bm[16] = loop
out['gram_dev'] = float(np.abs(Bm@Bm.T - np.eye(17)).max())
import su2plaq.rishon.operators as O
import su2plaq.rishon.observables as Ob
res = {}
obs = json.load(open('results/rishon/observables.json'))
cs = obs['closed_spectra']
assert cs['g2'] == [0.5, 1.0, 2.0]
def group(ev, tol=1e-9):
    vals, mult = [], []
    for e in np.sort(ev):
        if vals and abs(e - vals[-1][0]) <= tol: vals[-1][1] += 1; vals[-1][0] = None or vals[-1][0]
        else: vals.append([float(e), 1])
    return [v[0] for v in vals], [v[1] for v in vals]
for gi, g2 in enumerate(cs['g2']):
    H = 0.5*g2*np.diag(HE) + HB/g2
    blk = Bm@H@Bm.T
    inv = float(np.abs(H@Bm.T - Bm.T@blk).max())          # invariance: H B^T = B^T (B H B^T)
    ev = np.linalg.eigvalsh(blk)
    vals, mult = group(ev)
    prod_blk = O.closed_block_full(g2)
    prod = Ob.closed_spectra((g2,))['rishon'][g2]
    js = cs['rishon'][gi]
    entry = {'span_invariance_residual': inv, 'own_eigs': vals, 'own_mult': mult,
             'block_diff_vs_prod': float(np.abs(prod_blk - blk).max()),
             'prod_closed_spectra_eigs_diff': float(np.abs(np.array(prod['eigenvalues']) - np.array(vals)).max()),
             'prod_mult': prod['multiplicities'],
             'json_eigs_diff': float(np.abs(np.array(js['eigenvalues']) - np.array(vals)).max()),
             'json_mult': js['multiplicities'],
             'formula_diff': float(np.abs(np.array([0.75*g2 - np.sqrt(9/16*g2**2 + 32/g2**2), 0.0, 0.75*g2 + np.sqrt(9/16*g2**2 + 32/g2**2)]) - np.array(vals)).max()),
             'full_unsorted_eig_diff': float(np.abs(np.sort(np.linalg.eigvalsh(prod_blk)) - np.sort(ev)).max())}
    entry['all_ok'] = bool(entry['block_diff_vs_prod'] <= 1e-12 and entry['prod_closed_spectra_eigs_diff'] <= 1e-12 and entry['json_eigs_diff'] <= 1e-12
                           and mult == [1, 15, 1] == prod['multiplicities'] == js['multiplicities'])
    res[str(g2)] = entry
out['by_g2'] = res
# invariance-check firing: three out-of-sector perturbations of H_B^in, applied to the production routine (monkeypatch)
orig = O.h_magnetic_inner
outside = [k for k in range(1296) if k not in vi and abs(loop[k]) < 1e-12]
fire = {}
def try_perturb(name, i, j):
    bad = orig().copy(); bad[i, j] += 1e-3; bad[j, i] += 1e-3
    O.h_magnetic_inner = lambda: bad
    try:
        O.closed_block_full(1.0); r = 'NOT_RAISED'
    except ValueError as e: r = 'ValueError: ' + str(e)[:80]
    finally: O.h_magnetic_inner = orig
    fire[name] = r
try_perturb('vac_k(k=5) <-> outside code, 1e-3', vi[5], outside[0])
try_perturb('loop_support_code <-> outside code, 1e-3', int(np.flatnonzero(np.abs(loop) > 1e-12)[0]), outside[3])
try_perturb('vacA <-> outside code, 1e-3', ia, outside[10])
# determinant-like term: add a coupling between two vacuum codes (stays in sector) -> must NOT raise but change spectrum
bad = orig().copy(); bad[vi[1], vi[2]] += 0.5; bad[vi[2], vi[1]] += 0.5
O.h_magnetic_inner = lambda: bad
try:
    Hb = O.closed_block_full(1.0); fire['in-sector coupling vac1<->vac2 (should not raise)'] = {'raised': False, 'offdiag_in_block': float(Hb[1, 2].real)}
except ValueError as e: fire['in-sector coupling'] = {'raised': True, 'msg': str(e)}
finally: O.h_magnetic_inner = orig
out['invariance_firing'] = fire
out['all_ok'] = bool(all(r['all_ok'] for r in res.values()) and out['n_vac_codes'] == 16 and out['HE_zero_equals_vac'] and out['gram_dev'] <= 1e-12
                     and all(v.startswith('ValueError') for k, v in fire.items() if isinstance(v, str)))
json.dump(out, open('results/rishon/tester-208-closed-block.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
