"""Independent verification of M0 step 0.4 (physical states, route A).  Tester script, not collected by pytest.
Uses su2plaq.exact.physical ONLY to read the object under test (basis.keys/amps/labels, to_convention, s_o_dims,
inner_span).  Geometry, Casimirs, generators, Gram, Paulo basis, counts are built here from scratch.
Run: python tests/independent/check_physical_0_4.py  (seed 20261104)"""
import itertools, json, subprocess, sys, time
import numpy as np
import scipy.sparse as sp

sys.path.insert(0, "src")
from su2plaq.exact import physical as P

SEED = 20261104
rng = np.random.default_rng(SEED)
out = {"seed": SEED, "commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()}

# ---------------------------------------------------------------- own geometry (METHODS §1 coordinates)
LINKS = [  # (start, end), index 0..11
    ((0, 0), (1, 0)), ((1, 0), (1, 1)), ((0, 1), (1, 1)), ((0, 0), (0, 1)),   # b r t l
    ((-1, 0), (0, 0)), ((0, -1), (0, 0)),   # o0 o1 into (0,0)
    ((1, 0), (2, 0)), ((1, -1), (1, 0)),    # o2 out of (1,0), o3 into (1,0)
    ((1, 1), (2, 1)), ((1, 1), (1, 2)),     # o4 o5 out of (1,1)
    ((-1, 1), (0, 1)), ((0, 1), (0, 2)),    # o6 into (0,1), o7 out of (0,1)
]
SITES = [(0, 0), (1, 0), (1, 1), (0, 1)]
CORNERS = []
for s in SITES:
    ends = []
    for i, (a, b) in enumerate(LINKS):
        if a == s: ends.append((i, "L"))
        if b == s: ends.append((i, "R"))
    assert len(ends) == 4
    CORNERS.append(ends)
# far end: outer link starting at a corner has far end R, ending at a corner has far end L
OUTER_NEAR = {i: ("L" if LINKS[i][0] in SITES else "R") for i in range(4, 12)}

# ---------------------------------------------------------------- (1) independent count via total Casimir
sig = [np.array([[0, 1], [1, 0]], complex), np.array([[0, -1j], [1j, 0]]), np.array([[1, 0], [0, -1]], complex)]

def spin_mats(j):
    d = int(round(2 * j + 1))
    m = np.array([j - k for k in range(d)])
    jp = np.zeros((d, d))
    for k in range(1, d):
        jp[k - 1, k] = np.sqrt(j * (j + 1) - m[k] * (m[k] + 1))
    return [(jp + jp.T) / 2, (jp - jp.T) / 2j, np.diag(m).astype(complex)]

_sd = {}
def singlet_dim(js):
    key = tuple(sorted(js))
    if key in _sd: return _sd[key]
    dims = [int(round(2 * j + 1)) for j in key]
    D = int(np.prod(dims))
    S = [np.zeros((D, D), complex) for _ in range(3)]
    for q, j in enumerate(key):
        ms = spin_mats(j)
        for a in range(3):
            f = np.array([[1.0 + 0j]])
            for r, d in enumerate(dims):
                f = np.kron(f, ms[a] if r == q else np.eye(d))
            S[a] += f
    ev = np.linalg.eigvalsh(sum(s @ s for s in S))
    _sd[key] = int((np.abs(ev) < 1e-8).sum())
    return _sd[key]

t0 = time.time()
dim = closed = strings = amb = weighted = 0
mult = {}
for jc in itertools.product([0.0, 0.5], repeat=12):
    n = 1
    for ends in CORNERS:
        n *= singlet_dim([jc[i] for i, _ in ends])
        if n == 0: break
    if n:
        mult[jc] = n
        dim += n; strings += 1; amb += (n > 1)
        closed += n * all(x == 0 for x in jc[4:])
        weighted += n * int(np.prod([2 * x + 1 for x in jc[4:]]))
out["count_independent"] = dict(dim=dim, closed=closed, link_strings=strings, ambiguous=amb, far_end_weighted=weighted,
                                seconds=round(time.time() - t0, 2))
print("independent counts:", out["count_independent"])

t0 = time.time()
basis = P.physical_basis(jmax=0.5, convention="cg")
out["basis_build_seconds"] = round(time.time() - t0, 2)
# label-set vs independent multiplicities
from collections import Counter
cnt = Counter(l[0] for l in basis.labels)
out["labels_multiplicity_matches_independent"] = (dict(cnt) == mult)
print("builder labels' string multiplicities == independent product-of-singlet-dims:", dict(cnt) == mult)

# ---------------------------------------------------------------- own local operators (5-dim link space, jmax = 1/2)
# local order [(0,0,0),(1/2,+,+),(1/2,+,-),(1/2,-,+),(1/2,-,-)]; colour 0 = +1/2
T = [s / 2 for s in sig]
def local_gen(kind):
    ops = []
    for a in range(3):
        M = np.zeros((5, 5), complex)
        blk = np.kron(-T[a].T, np.eye(2)) if kind == "L" else np.kron(np.eye(2), T[a])  # (mL,mR) mL-major
        M[1:, 1:] = blk
        ops.append(M)
    return ops
GEN = {"L": local_gen("L"), "R": local_gen("R")}

def apply_local(vec, link, M):  # vec: dict key->amp
    p = 5 ** link
    res = {}
    for k, v in vec.items():
        s = (k // p) % 5
        base = k - s * p
        col = M[:, s]
        for s2 in np.nonzero(np.abs(col) > 1e-15)[0]:
            kk = base + int(s2) * p
            res[kk] = res.get(kk, 0) + col[s2] * v
    return res

def add(d1, d2):
    r = dict(d1)
    for k, v in d2.items(): r[k] = r.get(k, 0) + v
    return r

def to_dict(keys, amps): return {int(k): complex(a) for k, a in zip(keys, amps)}

def gauss_res(vec, gens):
    w = 0.0
    for ends in CORNERS:
        for a in range(3):
            tot = {}
            for link, side in ends:
                tot = add(tot, apply_local(vec, link, gens[side][a]))
            w = max(w, float(np.sqrt(sum(abs(x) ** 2 for x in tot.values()))))
    return w

# ---------------------------------------------------------------- (2) Gauss on >= 50 random states, Gram on all
N = len(basis.labels)
samp = sorted(rng.choice(N, size=60, replace=False).tolist())
res = []
for k in samp:
    res.append(gauss_res(to_dict(basis.keys[k], basis.amps[k]), GEN))
out["gauss_sample"] = dict(n=len(samp), max_residual=max(res), indices=samp)
print(f"Gauss (own generators, 4 corners x 3 a) on {len(samp)} random states: max {max(res):.2e}")

# negative control: flip sign of one component -> must violate
k = int(np.argmax([len(x) for x in basis.keys])); v = to_dict(basis.keys[k], basis.amps[k]); kk = list(v)[0]; v2 = dict(v); v2[kk] = -v2[kk]
neg = gauss_res(v2, GEN)
out["gauss_negative_control"] = neg
print(f"negative control (one sign flipped): residual {neg:.3f} (must be >> 1e-10)")

# Gram on all 433
rows, cols, vals = [], [], []
for c, (kx, ax) in enumerate(zip(basis.keys, basis.amps)):
    assert len(np.unique(kx)) == len(kx)
    rows.append(np.asarray(kx, np.int64)); cols.append(np.full(len(kx), c)); vals.append(np.asarray(ax, complex))
rows = np.concatenate(rows); cols = np.concatenate(cols); vals = np.concatenate(vals)
uk, inv = np.unique(rows, return_inverse=True)
A = sp.csr_matrix((vals, (inv, cols)), shape=(len(uk), N))
Gm = (A.conj().T @ A).toarray()
out["gram_max_dev"] = float(np.abs(Gm - np.eye(N)).max())
print(f"Gram: max|G-1| over all {N} states = {out['gram_max_dev']:.2e}")
# max components, real amps, far-end convention
out["max_components"] = int(max(len(k) for k in basis.keys))
out["max_imag"] = float(max(np.abs(a.imag).max() for a in basis.amps))
bad_far = 0
for kx in basis.keys:
    for i in range(4, 12):
        s = (np.asarray(kx) // 5 ** i) % 5
        ok = (s == 0) | (np.isin(s, [1, 3]) if OUTER_NEAR[i] == "L" else np.isin(s, [1, 2]))
        # near L (starts at corner) -> far is R: need mR=+ -> local idx 1 (++) or 3 (-+); near R -> far L=+ -> idx 1 or 2
        bad_far += int((~ok).sum())
out["far_end_violations"] = bad_far
print("max components:", out["max_components"], " max|Im|:", out["max_imag"], " far-end-convention violations:", bad_far)

# completeness: for sampled spin strings, nullity of own total Gauss operator on the far-fixed subspace == #states
def string_space(jc):
    """list of local-index choices per link (far-end fixed)."""
    ch = []
    for i, j in enumerate(jc):
        if j == 0: ch.append([0])
        elif i < 4: ch.append([1, 2, 3, 4])
        elif OUTER_NEAR[i] == "L": ch.append([1, 3])
        else: ch.append([1, 2])
    return ch

def nullity(jc):
    ch = string_space(jc)
    sizes = [len(c) for c in ch]; D = int(np.prod(sizes))
    keyof = lambda idx: sum(ch[i][idx[i]] * 5 ** i for i in range(12))
    allidx = list(itertools.product(*[range(s) for s in sizes]))
    keys = np.array([keyof(ix) for ix in allidx]); pos = {int(k): n for n, k in enumerate(keys)}
    Pm = sp.csr_matrix((D, D), dtype=complex)
    for ends in CORNERS:
        for a in range(3):
            Gm_ = sp.lil_matrix((D, D), dtype=complex)
            for n, k in enumerate(keys):
                for link, side in ends:
                    M = GEN[side][a]; p = 5 ** link; s = (int(k) // p) % 5
                    for s2 in np.nonzero(np.abs(M[:, s]) > 1e-15)[0]:
                        kk = int(k) - s * p + int(s2) * p
                        Gm_[pos[kk], n] += M[s2, s]
            Gm_ = Gm_.tocsr()
            Pm = Pm + Gm_.conj().T @ Gm_
    w = np.linalg.eigvalsh(Pm.toarray())
    return int((np.abs(w) < 1e-9).sum()), D

strs = sorted(mult)
cands = [s for s in strs if int(np.prod([len(c) for c in string_space(s)])) <= 2048]
pick = [cands[i] for i in rng.choice(len(cands), size=min(14, len(cands)), replace=False)]
# make sure at least some ambiguous ones are included
amb_c = [s for s in cands if mult[s] > 1]
pick += [amb_c[i] for i in rng.choice(len(amb_c), size=min(4, len(amb_c)), replace=False)]
comp = []
for s in pick:
    nu, D = nullity(s)
    comp.append(dict(string=[float(x) for x in s], dim_space=D, nullity=nu, n_basis=mult[s]))
    assert nu == mult[s] == cnt[s], (s, nu, mult[s], cnt[s])
out["completeness_nullity_vs_basis"] = comp
print(f"completeness: {len(comp)} spin strings (incl. {min(4,len(amb_c))} ambiguous), nullity of own Gauss operator == #basis states: all OK")

# ---------------------------------------------------------------- (3) Paulo convention, independent
# |0>_P=|0>_CG; |m m'>_P = s(m)s(m')|1/2,-m,-m'>_CG;  Paulo order [0,++,+-,-+,--]
perm = np.array([0, 4, 3, 2, 1]); sgn = np.array([1, 1, -1, -1, 1], float)
# V (CG->Paulo coords): psi_P[c] = sgn[c] * psi_CG[perm[c]]
def cg_to_paulo(vec):
    inv_perm = {int(perm[c]): c for c in range(5)}
    res = {}
    for k, v in vec.items():
        nk, na = 0, v
        for i in range(12):
            s = (k // 5 ** i) % 5
            c = inv_perm[s]
            nk += c * 5 ** i; na *= sgn[c]
        res[nk] = na
    return res
def paulo_to_cg(vec):
    res = {}
    for k, v in vec.items():
        nk, na = 0, v
        for i in range(12):
            c = (k // 5 ** i) % 5
            nk += int(perm[c]) * 5 ** i; na *= sgn[c]
        res[nk] = na
    return res
Vm = np.zeros((5, 5));
for c in range(5): Vm[c, perm[c]] = sgn[c]   # psi_P = Vm psi_CG
GENP = {s: [Vm @ g @ Vm.T for g in GEN[s]] for s in "LR"}

# independent validation of the Paulo-basis generators against Paulo Eq. 28 for U~
Ut = {}
for a, b in itertools.product(range(2), repeat=2):  # a,b in {+,-} -> 0,1
    M = np.zeros((5, 5), complex)
    sg = lambda x: 1 if x == 0 else -1
    M[1 + 2 * (1 - a) + (1 - b), 0] = sg(a) * sg(b) / np.sqrt(2)  # |0> -> |abar bbar>; Paulo idx of (m,m'): 1+2*m+m' (m=0 for +)
    M[0, 1 + 2 * a + b] = 1 / np.sqrt(2)
    Ut[(a, b)] = M
worst = 0
for a in range(3):
    for i in range(2):
        for j in range(2):
            lhs = GENP["L"][a] @ Ut[(i, j)] - Ut[(i, j)] @ GENP["L"][a]
            rhs = -sum(T[a][i, k] * Ut[(k, j)] for k in range(2))
            worst = max(worst, np.abs(lhs - rhs).max())
            lhs = GENP["R"][a] @ Ut[(i, j)] - Ut[(i, j)] @ GENP["R"][a]
            rhs = sum(Ut[(i, k)] * T[a][k, j] for k in range(2))
            worst = max(worst, np.abs(lhs - rhs).max())
out["paulo_generators_vs_eq28_commutator"] = float(worst)
print(f"own Paulo-basis generators vs [L,U~]=-(T U~), [R,U~]=+(U~ T) with Paulo Eq.28 U~: {worst:.2e}")

bp = P.to_convention(basis, "paulo")
back = P.to_convention(bp, "cg")
rt = pb = gp = 0.0
agree_own = 0.0
for k in samp:
    v_cg = to_dict(basis.keys[k], basis.amps[k])
    v_p = to_dict(bp.keys[k], bp.amps[k])
    mine = cg_to_paulo(v_cg)
    ks = set(mine) | set(v_p)
    agree_own = max(agree_own, max(abs(mine.get(q, 0) - v_p.get(q, 0)) for q in ks))
    gp = max(gp, gauss_res(v_p, GENP))
for k in range(N):
    v0 = to_dict(basis.keys[k], basis.amps[k]); v2 = to_dict(back.keys[k], back.amps[k])
    ks = set(v0) | set(v2)
    rt = max(rt, max(abs(v0.get(q, 0) - v2.get(q, 0)) for q in ks))
    assert back.labels[k] == basis.labels[k]
# own inverse
v0 = to_dict(basis.keys[samp[0]], basis.amps[samp[0]])
w = paulo_to_cg(cg_to_paulo(v0)); own_rt = max(abs(v0.get(q, 0) - w.get(q, 0)) for q in set(v0) | set(w))
# cg state fails Gauss with Paulo generators (neg control for convention)
kbig = int(np.argmax([len(x) for x in basis.keys])); vwrong = gauss_res(to_dict(basis.keys[kbig], basis.amps[kbig]), GENP)
out["paulo"] = dict(builder_matches_own_transform=agree_own, roundtrip_CG_P_CG_all433=rt, own_roundtrip=own_rt,
                    gauss_paulo_gens_on_paulo_states_60=gp, gauss_paulo_gens_on_CG_states_negctrl=vwrong)
print(f"to_convention: builder==own V transform {agree_own:.1e}; round trip all 433 {rt:.1e}; Gauss(Paulo gens) on Paulo states {gp:.1e}; neg-ctrl (CG state, Paulo gens) {vwrong:.2f}")

# discriminating negative controls for the convention: wrong signs / identity permutation must violate Gauss(Paulo gens)
def conv_variant(vec, perm_, sgn_):
    inv_p = {int(perm_[c]): c for c in range(5)}
    res = {}
    for k, v in vec.items():
        nk, na = 0, v
        for i in range(12):
            c = inv_p[(k // 5 ** i) % 5]; nk += c * 5 ** i; na *= sgn_[c]
        res[nk] = na
    return res
kbig = int(np.argmax([len(x) for x in basis.keys])); vb = to_dict(basis.keys[kbig], basis.amps[kbig])
nc_nosign = gauss_res(conv_variant(vb, perm, np.ones(5)), GENP)
nc_identity = gauss_res(vb, GENP)
nc_right = gauss_res(conv_variant(vb, perm, sgn), GENP)
out["paulo_convention_discrimination"] = dict(right=nc_right, no_signs=nc_nosign, no_permutation=nc_identity)
print(f"convention discrimination on the 1296-component state, Gauss(Paulo gens): right {nc_right:.1e}, signs dropped {nc_nosign:.3f}, permutation dropped {nc_identity:.3f}")

# ---------------------------------------------------------------- (4) S_o dims and inner span, own computation
allk = [np.asarray(k, np.int64) for k in basis.keys]
by_o = {}
for c, (kx, ax) in enumerate(zip(allk, basis.amps)):
    for o in np.unique(kx // 625):
        sel = kx // 625 == o
        by_o.setdefault(int(o), []).append((c, kx[sel] % 625, ax[sel]))
dims_own = {}
cols_all = []
for o, items in by_o.items():
    M = np.zeros((625, len(items)), complex)
    for c, (_, ik, a) in enumerate(items): M[ik, c] = a
    s = np.linalg.svd(M, compute_uv=False)
    dims_own[o] = int((s > 1e-9 * max(1, s[0])).sum())
    cols_all.append(M)
Mall = np.concatenate(cols_all, axis=1)
sv = np.linalg.svd(Mall, compute_uv=False)
rank_own = int((sv > 1e-9 * sv[0]).sum())
hist = Counter(dims_own.values())
# builder's
sod = P.s_o_dims(basis)
span = P.inner_span(basis)
agree = all(sod.get(o, 0) == dims_own.get(o, 0) for o in set(sod) | set(dims_own))
nz_builder = sum(1 for v in sod.values() if v > 0)
# outer patterns: outer key's per-link local index
closed_key = 0  # all outer j=0
out["S_o"] = dict(n_outer_keys_with_support_own=len(dims_own), n_entries_builder_table=len(sod), nonzero_builder=nz_builder,
                  histogram_dim_S_o={int(k): v for k, v in sorted(hist.items())}, rank_span_own=rank_own,
                  builder_inner_span_shape=list(span.shape), table_agrees=agree,
                  closed_pattern_dim_own=dims_own.get(closed_key), closed_pattern_dim_builder=sod.get(closed_key),
                  max_dim=max(dims_own.values()), sv_gap_around_rank=[float(sv[rank_own - 1]), float(sv[rank_own]) if rank_own < len(sv) else 0.0])
# builder's inner_span spans own span?
Q = span
resid = np.linalg.norm(Mall - Q @ (Q.conj().T @ Mall)) / np.linalg.norm(Mall)
out["S_o"]["span_residual_of_all_inner_components_in_builder_span"] = float(resid)
print("S_o:", json.dumps(out["S_o"], indent=1))

# numbers of outer keys: 6561 possible patterns per link j=0 (idx0) or 1/2 near m=+- (two idx) -> 3^8
poss = 3 ** 8
out["S_o"]["possible_outer_patterns"] = poss
json.dump(out, open("results/independent_check_physical_0_4.json", "w"), indent=1, default=str)
print("saved results/independent_check_physical_0_4.json")
