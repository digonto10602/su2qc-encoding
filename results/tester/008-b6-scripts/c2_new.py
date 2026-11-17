import sys, json, time, pathlib
sys.path.insert(0,"/home/digimonk/Projects/su2qc-encoding/src")
root=pathlib.Path(sys.argv[1]); outf=sys.argv[2]; encs=sys.argv[3:]
from su2plaq.compress import robust as RB
KIND={"twelve":"step","spinnet":"step","rishon":"step","fuzzy_ub":"UB","fuzzy_link":"UE","lsh":"step"}
out={}
for e in encs:
    t0=time.time()
    h=RB.headline(e,KIND[e],root=root,refresh=True)
    out[e]={"id":h["id"],"robust_key":list(h["robust_key"]),"t_mean":h["t_mean"],"archive_best":h["archive_best"],"archive_best_robust_key":list(h["archive_best_robust_key"]) if h["archive_best_robust_key"] else None,
      "unrankable":h["unrankable"],"ranking":[[r["id"],list(r["robust_key"]),r["t_mean"],r["angle_linear"],list(r["laptop_key"])] for r in h["ranking"]]}
    print(e,h["id"],h["robust_key"],h["t_mean"],"best",h["archive_best"],"unrank",h["unrankable"],f"{time.time()-t0:.0f}s",flush=True)
    json.dump(out,open(outf,"w"),indent=1)
