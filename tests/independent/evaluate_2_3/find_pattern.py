import numpy as np, itertools, json
from su2plaq.compress.spec import default_spec, get_encoding
enc = get_encoding("twelve")
eb = enc.physical_vectors()
spec = default_spec("twelve","step")
rng = np.random.default_rng(spec.trial_seed)
trial = set(np.sort(rng.choice(433, size=64, replace=False)).tolist())
print("trial subset size", len(trial))
best=None
rs = np.random.default_rng(1)
for it in range(20000):
    qs = sorted(rs.choice(28, size=int(rs.integers(3,7)), replace=False).tolist())
    # pick pattern from a random code of a random state not in trial
    k = int(rs.integers(433))
    if k in trial: continue
    c = int(eb.codes[k][rs.integers(len(eb.codes[k]))])
    pat = [(c>>q)&1 for q in qs]
    if not any(q<12 for q in qs) or any(q>=12 and pt==0 for q,pt in zip(qs,pat)): continue
    w = np.zeros(433)
    for kk in range(433):
        cc = eb.codes[kk]; m = np.ones(len(cc),bool)
        for q,p in zip(qs,pat): m &= ((cc>>q)&1)==p
        w[kk] = np.sum(np.abs(eb.amps[kk][m])**2)
    nz = np.flatnonzero(w>1e-12)
    if len(nz)==0: continue
    if any(int(x) in trial for x in nz): continue
    score = w.max()
    if best is None or score>best[0]:
        best=(score, qs, pat, nz.tolist(), w[nz].tolist())
        print(best)
    if score>0.3 and len(nz)<=40: break
json.dump({"qs":best[1],"pat":best[2],"states":best[3],"weights":best[4]}, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/pattern.json","w"))
