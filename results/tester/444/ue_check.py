"""Tester 444 (byproduct): own check of the proposer's claim 'U_E needs 4 rotations': on the 47 physical data codes, f(code) = sum_c N_n(c) = sum_c (l_pn + l_nv)
(own codes from own_sparse.mine, low 12 bits) is NOT in span{1, chi_a, chi_b} nor span{1, chi_a, chi_b, chi_c} for any 2 / 3 parity characters chi_S(code) = (-1)^{|S & code|}
over the 4095 non-empty bit sets S of the 12 data bits; f IS in the span for 4 (the 4 alpha phases: one per site, S = {l_pn, l_nv} of that site...).  Exact rank tests with sympy on a sample
and numpy residual projection on the full search.  No RNG."""
import sys, itertools, json, numpy as np
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/results/tester/444")
import own_sparse as OS
codes = sorted({c & 0xFFF for c in OS.mine}); assert len(codes) == 47
def nn(c): return sum(((c >> (3 * s)) & 1) + ((c >> (3 * s + 1)) & 1) for s in range(4))
f = np.array([nn(c) for c in codes], float)
ch = {}
for S in range(1, 4096):
    v = tuple((-1) ** (bin(S & c).count("1") & 1) for c in codes)
    if v not in ch and any(x != 1 for x in v) and tuple(-x for x in v) not in ch: ch[v] = S      # chi and -chi are the same direction
V = np.array(list(ch.keys()), float).T; S_of = list(ch.values()); n = V.shape[1]
print("47 codes, distinct non-constant characters up to sign:", n)
one = np.ones(47)
def resid(basis, y):
    Q, _ = np.linalg.qr(basis); return y - Q @ (Q.T @ y)
out = {"n_codes": 47, "n_distinct_nonconstant_characters_up_to_sign": n, "f_nonconstant": bool(np.ptp(f) > 0)}
# k = 1
out["k1_hits"] = [S_of[i] for i in range(n) if np.linalg.norm(resid(np.stack([one, V[:, i]], 1), f)) < 1e-9]
# k = 2
hits2 = []
for i in range(n):
    for j in range(i + 1, n):
        B = np.stack([one, V[:, i], V[:, j]], 1)
        if np.linalg.matrix_rank(B) == 3 and np.linalg.norm(resid(B, f)) < 1e-9: hits2.append((S_of[i], S_of[j]))
out["k2_hits"] = hits2
# k = 3 : for each pair, residual r of f; need chi_k with residual parallel to r
hits3 = []
for i in range(n):
    for j in range(i + 1, n):
        B = np.stack([one, V[:, i], V[:, j]], 1); Q, _ = np.linalg.qr(B); r = f - Q @ (Q.T @ f)
        nr = np.linalg.norm(r)
        if nr < 1e-9: continue
        R = V - Q @ (Q.T @ V); nR = np.linalg.norm(R, axis=0); ok = nR > 1e-9
        cosv = np.where(ok, np.abs(r @ R) / (nr * np.where(ok, nR, 1)), 0)
        for k in np.nonzero(cosv > 1 - 1e-10)[0]:
            if k > j: hits3.append((S_of[i], S_of[j], S_of[int(k)]))
out["k3_hits"] = hits3
# k = 4: the four alpha phases: S_c = bit 3c (l_pn) and bit 3c+1 (l_nv) per site -> f = sum_c N_n(c) is a sum of four 'two-bit sum' terms, but as parity characters: N = (1 - chi_pn)/2 + (1 - chi_nv)/2 per site
# (a site holds at most one of l_pn, l_nv) -> try to find 4 characters directly: f in span{1, chi_a..chi_d}: test the natural choice S = {l_pn(c), l_nv(c)} (= parity l_pn xor l_nv = N_n(c) since they are never both set)
def chiS(S): return np.array([(-1) ** (bin(S & c).count("1") & 1) for c in codes], float)
B4 = np.stack([one] + [chiS(0b011 << (3 * s)) for s in range(4)], 1)
out["k4_natural_residual"] = float(np.linalg.norm(resid(B4, f)))
print({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items()})
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/444/ue_check.json", "w"), indent=1)
