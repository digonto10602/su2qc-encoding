"""Independent numpy checks: (4) 625-code inner operator, (5) the 16 symmetries on the 433 states, outer-support numbers.
Own construction of Paulo's U (Eq. 28 of the notes: U_ab|ab>=|0>/sqrt2, U_ab|0>=s(a)s(b)|abar bbar>/sqrt2); no use of lean/exact.py."""
import json, sys, itertools, collections
import numpy as np, scipy.sparse as sp, scipy.sparse.csgraph as cg
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
out = {}
# ---- (4) inner operator on 625 codes
idx = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
bar = {0: 1, 1: 0}; s = {0: 1.0, 1: -1.0}
U = [[np.zeros((5, 5)) for _ in range(2)] for _ in range(2)]
for a in range(2):
    for b in range(2):
        U[a][b][0, idx[(a, b)]] = 1 / np.sqrt(2)
        U[a][b][idx[(bar[a], bar[b])], 0] = s[a] * s[b] / np.sqrt(2)
# W = sum_{a,b,c,e} U_b[a][b] U_r[b][c] (U_t[e][c])^dag (U_l[a][e])^dag
W = sp.csr_matrix((625, 625))
for a, b, c, e in itertools.product(range(2), repeat=4):
    m = [sp.csr_matrix(U[a][b]), sp.csr_matrix(U[b][c]), sp.csr_matrix(U[e][c].T), sp.csr_matrix(U[a][e].T)]
    k = sp.kron(m[3], sp.kron(m[2], sp.kron(m[1], m[0])))
    W = W + k
M = -(W + W.T).tocsr()   # real entries -> adjoint = transpose
M.eliminate_zeros()
dense = M.toarray()
off = sp.triu(M, k=1).tocoo()
mods = sorted(set(np.round(np.abs(off.data), 12)))
ncomp, labels = cg.connected_components(M != 0, directed=False)
sizes = sorted(collections.Counter(collections.Counter(labels).values()).items())
ev = np.linalg.eigvalsh(dense)
spec = {lam: int(np.sum(np.abs(ev - lam) < 1e-9)) for lam in (-2, -1, -0.5, 0, 0.5, 1, 2)}
out["inner625"] = dict(n_edges=int(off.nnz), n_diag=int(M.diagonal().astype(bool).sum()), edge_moduli=[float(x) for x in mods],
                       component_sizes=[[int(a), int(b)] for a, b in sizes], spectrum=spec, hermitian_err=float(abs(dense - dense.T).max()),
                       n_eig_outside=int(625 - sum(spec.values())))
print("inner625:", out["inner625"])
cert = json.load(open("/home/digimonk/Projects/su2qc-encoding/compress/lean/structure-cert.json"))
c = cert["inner625"]
match = (c["n_edges"] == out["inner625"]["n_edges"] and c["n_diag"] == out["inner625"]["n_diag"] and [float(eval(x)) for x in c["edge_moduli"]] == out["inner625"]["edge_moduli"]
         and c["component_sizes"] == out["inner625"]["component_sizes"] and {float(l): m for l, m in c["spectrum"]} == {float(k): v for k, v in spec.items()})
print("matches certificate claims:", match); out["inner625_matches_cert"] = bool(match)
# ---- (5) symmetries on the 433 states (project float route-A H_B, H_E, no Lean/exact)
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.operators import h_magnetic_phys, h_electric_inner, h_electric_outer
B = physical_basis()
HB, leak = h_magnetic_phys(B); HE = h_electric_inner(B); HEo = h_electric_outer(B)
n = B.dim; print("n states", n, "W leak", leak, "HB hermitian err", abs(HB - HB.conj().T).max())
spec_hb = np.linalg.eigvalsh(HB)
out["HB_spectrum"] = {str(lam): int(np.sum(np.abs(spec_hb - lam) < 1e-9)) for lam in (-2, -1, -0.5, 0, 0.5, 1, 2)}
print("HB spectrum", out["HB_spectrum"], "sum", sum(out["HB_spectrum"].values()))
sj = json.load(open("/home/digimonk/Projects/su2qc-encoding/compress/lean/structure.json"))
# labels of the cert vs project labels
labs = B.labels
jl = np.array([[int(round(2 * x)) for x in l[0]] for l in labs]); JL = np.array([[int(round(2 * x)) for x in l[1]] for l in labs])
cj = np.array([l["j2"] for l in cert["labels"]]); cJ = np.array([l["J2"] for l in cert["labels"]])
out["labels_match_project"] = bool((jl == cj).all() and (JL == cJ).all())
print("cert labels == project labels (order, 2j):", out["labels_match_project"])
corners = [[l for l, r in cc] for cc in cert["corners"]]
syms = []
for sy in sj["symmetries"]:
    p = np.array(sy["perm"]); sg = np.array(sy["signs"], float)
    S = np.zeros((n, n)); S[p, np.arange(n)] = sg          # S|k> = s_k |p_k>
    rHB = np.abs(S @ HB - HB @ S).max(); rHE = np.abs(S @ np.diag(HE) - np.diag(HE) @ S).max()
    unitary = np.abs(S.T @ S - np.eye(n)).max()
    # label action: find link permutation pi with j2_col[pi(i)](perm k) == j2_col[i](k)
    cols = {tuple(jl[:, i]): i for i in range(12)}
    img = jl[np.argsort(p)]            # state k' = p[k] carries label of k  -> label of image
    pi = []
    ok = True
    for i in range(12):
        t = tuple(jl[p, :][:, :].T[i]) if False else None
    # direct: column i of the image-labelled array
    jl_img = np.empty_like(jl); jl_img[p] = jl     # label (links) of state p[k] should equal pi-permuted label of k ... we instead search pi
    # for each i find j such that jl[p, j] == jl[:, i]  (state p[k] has at link j the value state k has at link i)
    for i in range(12):
        js = [j for j in range(12) if (jl[p, j] == jl[:, i]).all()]
        pi.append(js)
    uniq = all(len(x) >= 1 for x in pi)
    pi1 = [x[0] for x in pi]
    is_perm = sorted(pi1) == list(range(12))
    # automorphism of the incidence structure: corner link sets map to corner link sets, inner (0..3) to inner
    cs = [frozenset(c) for c in corners]
    maps_corners = is_perm and all(frozenset(pi1[l] for l in c) in cs for c in cs) and sorted(pi1[:4]) == [0, 1, 2, 3]
    syms.append(dict(name=sy["name"], res_HB=float(rHB), res_HE=float(rHE), res_HEouter=float(np.abs(HEo[p] - HEo).max()), unitary_err=float(unitary), link_perm=pi1,
                     link_perm_is_perm=bool(is_perm), maps_corner_structure=bool(maps_corners), perm_is_identity=bool((p == np.arange(n)).all())))
    print(f"{sy['name']:18s} |[S,HB]|={rHB:.1e} |[S,HE]|={rHE:.1e} |HEouter inv|={syms[-1]['res_HEouter']:.1e} unit={unitary:.1e} link_perm={pi1} perm={is_perm} corners={maps_corners} identity_perm={syms[-1]['perm_is_identity']}")
out["symmetries"] = syms
# distinct signed permutations
keys = collections.defaultdict(list)
for sy in sj["symmetries"]: keys[(tuple(sy["perm"]), tuple(sy["signs"]))].append(sy["name"])
out["distinct_signed_perms"] = [v for v in keys.values()]
print("distinct signed permutations:", len(keys), list(keys.values()))
# group closure: products of the listed signed perms stay in the list?
def comp(a, b):  # a after b
    pa, sa = np.array(a[0]), np.array(a[1]); pb, sb = np.array(b[0]), np.array(b[1])
    return (tuple(pa[pb]), tuple((sb * sa[pb]).astype(int)))
ks = set(keys)
out["closed_under_composition"] = all(comp(a, b) in ks for a in ks for b in ks)
print("closed under composition:", out["closed_under_composition"])
# negative control: a random signed permutation / a wrong sign must NOT commute
rng = np.random.default_rng(7)
p = np.arange(n); sg = np.ones(n); sg[3] = -1
S = np.zeros((n, n)); S[p, np.arange(n)] = sg
out["negctl_sign_flip_res"] = float(np.abs(S @ HB - HB @ S).max())
p2 = np.arange(n); p2[[0, 1]] = [1, 0]; S = np.zeros((n, n)); S[p2, np.arange(n)] = 1
out["negctl_swap_res"] = float(np.abs(S @ HB - HB @ S).max()); print("negative controls:", out["negctl_sign_flip_res"], out["negctl_swap_res"])
# ---- outer support (own computation): number of states per outer key vs dim S_o
keys_by_outer = collections.defaultdict(set)
for k, ks_ in enumerate(B.keys):
    for key in ks_: keys_by_outer[int(key) // 625].add(k)
cnt = collections.Counter(len(v) for v in keys_by_outer.values())
out["outer"] = dict(n_keys=len(keys_by_outer), max_states=max(len(v) for v in keys_by_outer.values()), hist_states_per_outer=sorted(cnt.items()))
from su2plaq.exact.physical import s_o_dims
d = s_o_dims(B)
h = collections.Counter(v for v in d.values() if v > 0)
out["outer"]["hist_dim_S_o_nonzero"] = sorted(h.items()); out["outer"]["n_dim_S_o_nonzero"] = sum(h.values())
print("outer:", out["outer"])
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
