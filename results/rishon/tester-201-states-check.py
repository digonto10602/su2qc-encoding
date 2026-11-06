"""Tester 201: audit of the production basis with my own operators (own JW, own geometry from coordinates)."""
import itertools, json, subprocess, time, sys
import numpy as np, scipy.sparse as sp
sys.path.insert(0, "src")
import importlib.util
spec = importlib.util.spec_from_file_location("ind", "results/rishon/tester-201-independent-counts.py")
ind = importlib.util.module_from_spec(spec); spec.loader.exec_module(ind)
from su2plaq.rishon.physical import rishon_basis
from su2plaq.rishon.operators import inner_codes

t0 = time.time(); B = rishon_basis(); tb = time.time() - t0
out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "build_s": tb, "dim": B.dim}
LK, CORN = ind.LK, ind.CORN
M4 = [ind.end_gens(8)[0][a][0][np.ix_(range(4), range(4))] for a in range(3)]   # 4x4 end generators (own JW)
# valid link codes
SECT = {3: 'A', 12: 'B', 5: 'Q', 6: 'Q', 9: 'Q', 10: 'Q'}
lens = np.array([len(k) for k in B.keys]); sid = np.repeat(np.arange(B.dim), lens)
key = np.concatenate(B.keys).astype(np.int64); amp = np.concatenate(B.amps)
out["coo_entries"] = int(len(key)); out["key_max"] = int(key.max())
# (1) valid link codes, every key
lc = np.stack([(key >> (4 * l)) & 15 for l in range(12)], axis=1)
ok_codes = np.isin(lc, list(SECT)).all()
out["all_link_codes_valid"] = bool(ok_codes)
# (2) outer far ends: A/B -> far full/empty (set by type), Q -> far colour 1 = bits '01' ; near end determined by type
far_ok = True; near_ok = True
for l in range(4, 12):
    cs, ce, _ = LK[l]; near = 'L' if cs is not None else 'R'
    farsh = 2 if near == 'L' else 0
    code = lc[:, l]
    far = (code >> farsh) & 3; nearv = (code >> (2 - farsh)) & 3
    typ = np.vectorize(SECT.get)(code)
    # type A: L full R empty ; B: L empty R full
    expect_far = np.where(typ == 'Q', 1, np.where(typ == 'A', 3 if farsh == 0 else 0, 0 if farsh == 0 else 3))
    far_ok &= bool((far == expect_far).all())
out["outer_far_end_spectator_rule"] = far_ok
# (3) occupations conserved per corner within each state; charges
def corner_occ(c):
    return sum(((key >> (4 * l + (0 if s == 'L' else 2))) & 3) % 3 % 3 * 0 + (((key >> (4 * l + (0 if s == 'L' else 2))) & 1) + ((key >> (4 * l + (0 if s == 'L' else 2) + 1)) & 1)) for l, s in CORN[c])
qc = np.stack([corner_occ(c) for c in range(4)], axis=1)
first = np.concatenate([[0], np.cumsum(lens)[:-1]])
out["charge_constant_within_state"] = bool((qc == np.repeat(qc[first], lens, axis=0)).all())
qs = qc[first]
out["own_n_u1_sectors"] = int(len({tuple(r) for r in qs})); out["own_u2_sector"] = int(np.all(qs == 4, axis=1).sum())
out["production_charge_agrees"] = bool(all(B.u1_charges(k) == tuple(qs[k]) for k in range(0, B.dim, 37)))
# own closed count : outer links not Q
typ_arr = np.array([[SECT[int(c)] for c in lc[first[k]]] for k in range(B.dim)])
out["own_closed"] = int(np.all(typ_arr[:, 4:] != 'Q', axis=1).sum())
out["own_type_patterns"] = len({tuple(r) for r in typ_arr})
out["labels_unique"] = len(set(B.labels)) == B.dim
out["label_types_match_keys"] = bool(all(tuple(B.labels[k][0]) == tuple(typ_arr[k]) for k in range(B.dim)))
# (4) Gauss residual on ALL states with own operators (vectorised over COO with state ids)
def apply_end(sid_, key_, amp_, q0, M):
    sub = (key_ >> q0) & 3; base = key_ & ~(np.int64(3) << q0)
    S, K, A = [], [], []
    for r in range(4):
        coef = M[r][sub]; nz = np.abs(coef) > 1e-15
        if nz.any():
            S.append(sid_[nz]); K.append(base[nz] | (np.int64(r) << q0)); A.append(amp_[nz] * coef[nz])
    if not S: return sid_[:0], key_[:0], amp_[:0]
    return np.concatenate(S), np.concatenate(K), np.concatenate(A)
def norm2_per_state(S, K, A, n):
    if len(S) == 0: return np.zeros(n)
    comb = S.astype(np.int64) * (1 << 48) * 0 + 0
    order = np.lexsort((K, S)); S, K, A = S[order], K[order], A[order]
    st = np.flatnonzero(np.concatenate(([True], (S[1:] != S[:-1]) | (K[1:] != K[:-1]))))
    tot = np.add.reduceat(A, st)
    return np.bincount(S[st], weights=np.abs(tot) ** 2, minlength=n)
t0 = time.time(); gmax = np.zeros(B.dim)
for c in range(4):
    for a in range(3):
        Ss, Ks, As = [], [], []
        for (l, s) in CORN[c]:
            q0 = 4 * l + (0 if s == 'L' else 2)
            S, K, A = apply_end(sid, key, amp, q0, M4[a]); Ss.append(S); Ks.append(K); As.append(A)
        n2 = norm2_per_state(np.concatenate(Ss), np.concatenate(Ks), np.concatenate(As), B.dim)
        gmax = np.maximum(gmax, np.sqrt(n2))
out["gauss_max_all_states_own_ops"] = float(gmax.max()); out["gauss_time_s"] = time.time() - t0
# negative control: break a state (swap two amplitudes' sign on one entry) -> residual must be >> 1e-10
k = int(np.argmax(lens)); amp2 = amp.copy(); amp2[first[k]+1] *= -1
msk = sid == k
gm = 0.0
for c in range(4):
    for a in range(3):
        Ss, Ks, As = [], [], []
        for (l, s) in CORN[c]:
            q0 = 4 * l + (0 if s == 'L' else 2)
            S, K, A = apply_end(sid[msk], key[msk], amp2[msk], q0, M4[a]); Ss.append(S); Ks.append(K); As.append(A)
        n2 = norm2_per_state(np.concatenate(Ss), np.concatenate(Ks), np.concatenate(As), B.dim)
        gm = max(gm, float(np.sqrt(n2[k])))
out["negative_control_gauss_residual_sign_flipped_entry"] = gm
out["negative_control_state_ncomp"] = int(len(B.keys[k]))
# (5) norms and FULL Gram
nrm = np.sqrt(np.bincount(sid, weights=np.abs(amp) ** 2, minlength=B.dim)); out["norm_dev_max"] = float(np.abs(nrm - 1).max())
uk, col = np.unique(key, return_inverse=True)
M = sp.csr_matrix((amp, (sid, col)), shape=(B.dim, len(uk)))
t0 = time.time(); G = (M @ M.conj().T).tocsr(); out["gram_time_s"] = time.time() - t0
G = G - sp.identity(B.dim, format="csr")
out["gram_offdiag_max_full"] = float(np.abs(G.data).max()) if G.nnz else 0.0
out["n_distinct_keys"] = int(len(uk))
# (6) J labels: pair-Casimir of ends (0,1) of each corner on a sample, vs the label
rng = np.random.default_rng(201)
samp = rng.choice(B.dim, 1500, replace=False)
bad = 0; maxd = 0.0
for k in samp:
    ks = B.keys[k]; as_ = B.amps[k]; labJ = B.labels[k][1]
    for c in range(4):
        ends = CORN[c]
        # production corner ends order: inner pair first then outer pair; ends 0,1 are the two inner-link ends
        # (inner links indices < 4); own order of CORN[c] is by link index with side -> take the two with link<4
        pair = [(l, s) for (l, s) in ends if l < 4]
        assert len(pair) == 2
        tot = 0.0
        Ss, Ks, As = {}, {}, {}
        res = 0.0
        for a in range(3):
            S, K, A = [], [], []
            for (l, s) in pair:
                q0 = 4 * l + (0 if s == 'L' else 2)
                s_, k_, a_ = apply_end(np.zeros(len(ks), dtype=np.int64), ks, as_, q0, M4[a]); S.append(s_); K.append(k_); A.append(a_)
            res += norm2_per_state(np.concatenate(S), np.concatenate(K), np.concatenate(A), 1)[0]
        Jlab = labJ[c]
        maxd = max(maxd, abs(res - Jlab * (Jlab + 1)))
        # note: (G0+G1)^2 expectation = ||G0 psi+G1 psi||^2 summed over a
out["J_label_vs_pair_casimir_max_dev_1500_states"] = float(maxd)
# (7) inner span rank (own): Gram of inner components over (state, outer pattern)
codes = inner_codes(); pos = {int(c): i for i, c in enumerate(codes)}
inner = key & 0xFFFF; outerk = key >> 16
cid = sid.astype(np.int64) * (1 << 32) + outerk
_, colc = np.unique(cid, return_inverse=True)
rows = np.searchsorted(codes, inner); assert (codes[rows] == inner).all()
Z = sp.csr_matrix((amp, (rows, colc)), shape=(1296, colc.max() + 1))
Gi = (Z @ Z.conj().T).toarray(); w = np.linalg.eigvalsh((Gi + Gi.conj().T) / 2)
out["inner_span_n_columns"] = int(colc.max() + 1)
out["inner_gram_eig_min"] = float(w.min()); out["inner_gram_eig_max"] = float(w.max())
out["inner_rank_1e-9"] = int((w > 1e-9 * w.max()).sum()); out["inner_rank_1e-6"] = int((w > 1e-6 * w.max()).sum())
srt = np.sort(w); out["inner_gram_second_smallest"] = float(srt[1])
# own inner codes
own_codes = np.array(sorted(sum(c << (4 * l) for l, c in enumerate(cfg)) for cfg in itertools.product([3, 5, 6, 9, 10, 12], repeat=4)))
out["inner_codes_equal_own"] = bool(np.array_equal(own_codes, codes))
# distinct outer patterns used
out["n_outer_patterns_used"] = int(len(np.unique(outerk)))
print(json.dumps(out, indent=1)); json.dump(out, open("results/rishon/tester-201-states-check.json", "w"), indent=1)
