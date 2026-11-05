"""Tester script (not collected by pytest): independent dim S_o 6561-table check, M1 step 1.8.
Uses su2plaq only to read the object under test (basis.keys/amps, s_o_dims, outer_patterns, inner_span)."""
import itertools, json, subprocess, sys
from collections import Counter
import numpy as np
sys.path.insert(0, "src")
from su2plaq.exact import physical as P

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()}
# own geometry (from check_physical_0_4.py): outer links 4..11; near end L for links that start at a corner
LINKS = [((0,0),(1,0)),((1,0),(1,1)),((0,1),(1,1)),((0,0),(0,1)),((-1,0),(0,0)),((0,-1),(0,0)),((1,0),(2,0)),((1,-1),(1,0)),
         ((1,1),(2,1)),((1,1),(1,2)),((-1,1),(0,1)),((0,1),(0,2))]
SITES = [(0,0),(1,0),(1,1),(0,1)]
NEAR = {i: ("L" if LINKS[i][0] in SITES else "R") for i in range(4, 12)}
# local order CG [(0,0,0),(1/2,+,+),(1/2,+,-),(1/2,-,+),(1/2,-,-)]: index = 1+2*(mL idx)+(mR idx)
# far end fixed +: near L -> far R=+ -> idx 1,3 ; near R -> far L=+ -> idx 1,2
cg_allowed = {i: [0, 1, 3] if NEAR[i] == "L" else [0, 1, 2] for i in NEAR}
perm = np.array([0, 4, 3, 2, 1])               # Paulo index c <- CG index perm[c]
cg2p = {int(perm[c]): c for c in range(5)}
p_allowed = {i: sorted(cg2p[x] for x in v) for i, v in cg_allowed.items()}
def patterns(allowed):
    res = []
    for combo in itertools.product(*[allowed[i] for i in range(4, 12)]):
        res.append(sum(c * 5 ** (i - 4) for i, c in zip(range(4, 12), combo)))
    return sorted(res)

def dims_for(basis, allowed):
    pats = patterns(allowed)
    assert len(pats) == 6561 and len(set(pats)) == 6561
    by_o = {}
    for c, (kx, ax) in enumerate(zip(basis.keys, basis.amps)):
        kx = np.asarray(kx, np.int64)
        for o in np.unique(kx // 625):
            sel = kx // 625 == o
            by_o.setdefault(int(o), []).append((kx[sel] % 625, ax[sel]))
    stray = [o for o in by_o if o not in set(pats)]
    dims = {o: 0 for o in pats}
    Mall = []
    for o, items in by_o.items():
        M = np.zeros((625, len(items)), complex)
        for c, (ik, a) in enumerate(items): M[ik, c] = a
        s = np.linalg.svd(M, compute_uv=False)
        if o in dims: dims[o] = int((s > 1e-9 * max(1, s[0])).sum())
        Mall.append(M)
    sv = np.linalg.svd(np.concatenate(Mall, axis=1), compute_uv=False)
    rank = int((sv > 1e-9 * sv[0]).sum())
    return dims, stray, rank, (float(sv[rank-1]), float(sv[rank]) if rank < len(sv) else 0.0)

res = {}
for conv, allowed in (("cg", cg_allowed), ("paulo", p_allowed)):
    basis = P.physical_basis(convention=conv)
    dims, stray, rank, gap = dims_for(basis, allowed)
    sod = P.s_o_dims(basis)
    op = P.outer_patterns(basis)
    hist = dict(sorted(Counter(dims.values()).items()))
    res[conv] = dict(n_own=len(dims), n_builder=len(sod), table_equal=(dims == {int(k): int(v) for k, v in sod.items()}),
                     patterns_equal=(op == patterns(allowed)), stray_outer_keys_outside_my_set=len(stray),
                     hist=hist, rank=rank, sv_gap=gap, closed_dim=dims[0], max=max(dims.values()),
                     span_shape=list(P.inner_span(basis).shape), dims=dims)
    print(conv, {k: v for k, v in res[conv].items() if k != "dims"})
# CG <-> Paulo table correspondence under my own map of outer keys
mp = {}
for conv in ("cg", "paulo"): pass
def remap(o):
    k = 0
    for i in range(4, 12):
        c = (o // 5 ** (i - 4)) % 5
        k += cg2p[c] * 5 ** (i - 4)
    return k
corr = all(res["cg"]["dims"][o] == res["paulo"]["dims"][remap(o)] for o in res["cg"]["dims"])
print("CG table == Paulo table under own outer-key map:", corr)
res["cg_paulo_correspond"] = corr
for c in ("cg", "paulo"): res[c]["dims"] = {str(k): v for k, v in res[c]["dims"].items()}
out.update(res)
json.dump(out, open("results/m1_step_1_8_so_table_independent.json", "w"), indent=1)
