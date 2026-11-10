"""Tester 202: independent encoding checks (codec, 38432 vectors Gauss with own end generators, closed target)."""
import itertools, json, subprocess, sys, time
import numpy as np, scipy.sparse as sp
from scipy.linalg import expm
sys.path.insert(0, 'src')
t0 = time.time()
out = {'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()}
from su2plaq.encodings.rishon import RishonEncoding, RISHON_NOMINAL
enc = RishonEncoding()
# ---- own W (global 16-mode JW), HE
Z = sp.csr_matrix(np.diag([1., -1.])); I2 = sp.identity(2, format='csr'); SM = sp.csr_matrix(np.array([[0, 1], [0, 0]], float))
def kronle(ops):
    o = sp.identity(1, format='csr')
    for x in ops: o = sp.kron(x, o, format='csr')
    return o
n = 16
c = [kronle([Z]*k + [SM] + [I2]*(n-k-1)) for k in range(n)]; cd = [x.T.tocsr() for x in c]
U = lambda l, i, j: c[4*l+i] @ cd[4*l+2+j]
codes = np.array(sorted(sum(s << (4*l) for l, s in enumerate(cfg)) for cfg in itertools.product([x for x in range(16) if bin(x).count('1') == 2], repeat=4)), dtype=np.int64)
Wf = sp.csr_matrix((2**n, 2**n))
for a, b, cc, d in itertools.product(range(2), repeat=4):
    Wf = Wf + U(0, a, b) @ U(1, b, cc) @ U(2, d, cc).T @ U(3, a, d).T
W = Wf[codes][:, codes].toarray(); HB = -(W + W.T)
nt = lambda x: 'A' if x == 3 else 'B' if x == 12 else 'Q'
HE = np.array([0.75*sum(nt((int(cc) >> (4*l)) & 15) == 'Q' for l in range(4)) for cc in codes])
# ---- codec
ref_set = set(codes.tolist())
cl = enc.physical_vectors('closed')
outer = int(cl.codes[0][0]) >> 16
out['outer_near_empty_code_from_closed_state0'] = hex(outer)
out['all_closed_states_share_outer_bits'] = bool(all(len(set((np.asarray(k) >> 16).tolist())) == 1 and int(k[0]) >> 16 == outer for k in cl.codes))
bad = 0; typ_bad = 0
for x in range(65536):
    dec = enc.decode(x | (outer << 16))
    if (dec is not None) != (x in ref_set): bad += 1
    elif dec is not None and tuple(dec[:4]) != tuple(nt((x >> (4*l)) & 15) for l in range(4)): typ_bad += 1
out['codec_inner_valid_set_mismatch_over_65536'] = bad
out['codec_inner_type_mismatch'] = typ_bad
out['inner_codes_equal_own'] = bool(np.array_equal(enc.inner_codes(), codes))
out['inner_codes_sorted_unique_int64'] = bool(enc.inner_codes().dtype == np.int64 and np.all(np.diff(enc.inner_codes()) > 0))
# bijection codes <-> types: decode is 1-1 between the 1296 inner codes and the 6^4 type/colour classes
decs = {enc.decode(int(x) | (outer << 16)) for x in codes}
out['n_distinct_decodes_on_inner_codes'] = len(decs)
# outer nibbles: count valid per outer link
cnt = []
for k in range(8):
    v = 0
    for nib in range(16):
        cd_ = (int(codes[0]) | (outer << 16)) & ~(0xF << (16+4*k)) | (nib << (16+4*k))
        v += enc.decode(cd_) is not None
    cnt.append(v)
out['valid_nibbles_per_outer_link'] = cnt
out['out_of_range_invalid'] = bool(enc.decode(1 << 48) is None and enc.decode(-1) is None)
# ---- physical vectors
eb = enc.physical_vectors('all')
N = len(eb.codes); out['n_vectors'] = N
norms = np.array([np.linalg.norm(a) for a in eb.amps]); out['norm_dev_max'] = float(np.abs(norms - 1).max())
allk = np.concatenate([np.asarray(k, dtype=np.int64) for k in eb.codes]); out['all_keys_valid_decode'] = bool(np.all(enc._type_indices(allk) >= 0))
out['keys_dtype_int64'] = bool(all(k.dtype == np.int64 for k in eb.codes[:100]))
# own Gauss: end generator on 2 qubits (bit0 = colour1): sum_ij T_ij c^dag_i c_j with own 2-mode JW
c2 = [kronle([Z]*k + [SM] + [I2]*(2-k-1)).toarray() for k in range(2)]
sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]
T = [s/2 for s in sig]
Eg = [sum(T[a][i, j]*(c2[i].T @ c2[j]) for i in range(2) for j in range(2)) for a in range(3)]
# geometry from METHODS sec 1 coordinates; links 0..11
coords = {0: ((0, 0), (1, 0)), 1: ((1, 0), (1, 1)), 2: ((0, 1), (1, 1)), 3: ((0, 0), (0, 1)),
          4: ((-1, 0), (0, 0)), 5: ((0, -1), (0, 0)), 6: ((1, 0), (2, 0)), 7: ((1, -1), (1, 0)),
          8: ((1, 1), (2, 1)), 9: ((1, 1), (1, 2)), 10: ((-1, 1), (0, 1)), 11: ((0, 1), (0, 2))}
sites = [(0, 0), (1, 0), (1, 1), (0, 1)]
ends = {s: [(l, 'L') for l, (a, b) in coords.items() if a == site] + [(l, 'R') for l, (a, b) in coords.items() if b == site] for s, site in enumerate(sites)}
out['ends_per_corner'] = {str(s): len(v) for s, v in ends.items()}
sid = np.concatenate([np.full(len(k), i, dtype=np.int64) for i, k in enumerate(eb.codes)])
amp = np.concatenate([np.asarray(a, dtype=complex) for a in eb.amps])
res = np.zeros(N)
for s in range(4):
    for a in range(3):
        ids, ks, vs = [], [], []
        for l, role in ends[s]:
            q0 = 4*l if role == 'L' else 4*l + 2
            pair = (allk >> q0) & 3
            for tgt in range(4):
                for src in range(4):
                    m = Eg[a][tgt, src]
                    if abs(m) < 1e-15: continue
                    sel = pair == src
                    ids.append(sid[sel]); ks.append((allk[sel] & ~(3 << q0)) | (tgt << q0)); vs.append(m*amp[sel])
        ids, ks, vs = map(np.concatenate, (ids, ks, vs))
        key = ids * (1 << 49) + ks
        uk, inv = np.unique(key, return_inverse=True)
        acc = np.zeros(len(uk), complex); np.add.at(acc, inv, vs)
        r2 = np.zeros(N); np.add.at(r2, uk // (1 << 49), np.abs(acc)**2)
        res = np.maximum(res, np.sqrt(r2))
out['gauss_residual_max_own_all_38432'] = float(res.max())
# orthogonality sample: Gram on 1500 random states (seed)
rng = np.random.default_rng(20261106)
sel = np.sort(rng.choice(N, 1500, replace=False)); out['gram_sample_seed'] = 20261106
rows = []
for i in sel:
    pass
maxoff = 0.0
M = sp.csr_matrix((amp, (sid, allk % (1 << 31) ))) if False else None
# exact sparse Gram via key indexing
uk, inv = np.unique(allk, return_inverse=True)
Psi = sp.csr_matrix((amp, (inv, sid)), shape=(len(uk), N))
Gm = (Psi.conj().T @ Psi).tocsr()
out['gram_minus_identity_max_ALL'] = float(abs(Gm - sp.identity(N)).max())
# ---- closed target
idx = np.arange(N)
closed = enc.physical_vectors('closed'); ncl = len(closed.codes); out['n_closed'] = ncl
import su2plaq.rishon.physical as P
cidx = P.closed_indices(enc.basis)
out['closed_idx_matches_closed_vectors'] = bool(all(np.array_equal(enc.basis.keys[k], closed.codes[j]) for j, k in enumerate(cidx)))
pos = {int(x): i for i, x in enumerate(codes)}
B = np.zeros((ncl, 1296), complex)
for r, (ks, am) in enumerate(zip(closed.codes, closed.amps)):
    for kk, aa in zip(ks, am): B[r, pos[int(kk) & 0xFFFF]] = aa
out['closed_B_orthonormal'] = float(np.abs(B.conj() @ B.T - np.eye(ncl)).max())
res_out = {}
for al, be in [(0.37, 0.61), (1.70, 1.00)]:
    UBe = expm(-1j*be*HB); UEe = np.diag(np.exp(-1j*al*HE))
    for name, Vin, args in [('UB', UBe, ('UB', None, be, 1)), ('UE', UEe, ('UE', al, None, 1)), ('step1', UBe@UEe, ('step', al, be, 1)),
                            ('step2', np.diag(np.exp(-0.5j*al*HE))@UBe@np.diag(np.exp(-0.5j*al*HE)), ('step', al, be, 2))]:
        Vc = enc.target(*args, states=cidx)
        own = B.conj() @ Vin @ B.T
        res_out[f'{name}@{al},{be}'] = {'shape': list(Vc.shape), 'unitarity': float(np.abs(Vc.conj().T@Vc - np.eye(ncl)).max()), 'vs_own_expm_restricted': float(np.abs(Vc - own).max())}
out['closed_target'] = res_out
out['closed_subspace_invariant_under_Vin_residual'] = float(np.abs(Vin@B.T - B.T@(B.conj()@Vin@B.T)).max())
# a non-closed subset (random 40 states) for target(states) vs own: general outer sums
sub = [int(i) for i in rng.choice(N, 40, replace=False)]
Bs = np.zeros((40, 1296, 1), complex)  # outer-resolved, own assembly
from collections import defaultdict
Vown = expm(-1j*0.61*HB)@np.diag(np.exp(-1j*0.37*HE))
S = np.zeros((40, 40), complex)
dd = []
for r, k in enumerate(sub):
    dct = defaultdict(lambda: np.zeros(1296, complex))
    for kk, aa in zip(enc.basis.keys[k], enc.basis.amps[k]): dct[int(kk) >> 16][pos[int(kk) & 0xFFFF]] += aa
    dd.append(dct)
for r in range(40):
    for s_ in range(40):
        S[r, s_] = sum(np.vdot(dd[r][o], Vown @ dd[s_][o]) for o in dd[r] if o in dd[s_])
Vt = enc.target('step', 0.37, 0.61, 1, states=sub)
out['target_40_random_states_vs_own'] = float(np.abs(Vt - S).max()); out['target_40_seed'] = 20261106
# inner view
iv = enc.inner_view(); ivb = iv.physical_vectors()
out['inner_view_1296_single_code'] = bool(len(ivb.codes) == 1296 and all(len(c_) == 1 and int(c_[0]) == int(codes[i]) for i, c_ in enumerate(ivb.codes)))
out['RISHON_NOMINAL'] = RISHON_NOMINAL
out['wall_s'] = time.time() - t0
json.dump(out, open('results/rishon/tester-202-encoding.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
