# run in OLD tree (e464c19): the track functions
import sys, json, time
tree=sys.argv[1]; sys.path.insert(0,tree+"/src")
import pathlib
root=pathlib.Path(tree)
out={}
t0=time.time()
from su2plaq.spinnet import loop as L
h=L.headline(root, refresh=True)
out["spinnet"]={"id":h["id"],"robust_key":list(h["robust_key"]),"t_mean":h["t_mean"],"archive_best":h["archive_best"],"unrankable":h.get("unrankable",[r["id"] for r in h["ranking"] if r["robust_key"] is None]),
  "ranking":[[r["id"],(list(r["robust_key"]) if r["robust_key"] else None),r["t_mean"],r["angle_linear"]] for r in h["ranking"]]}
print("spinnet",h["id"],h["robust_key"],h["t_mean"],time.time()-t0,flush=True)
from su2plaq.rishon.compress import robust as R
h=R.headline("step",root,True)
out["rishon"]={"id":h["id"],"robust_key":list(h["robust_key"]),"t_mean":h["t_mean"],"archive_best":h["archive_best"],"unrankable":h.get("unrankable",[r["id"] for r in h["ranking"] if r["robust_key"] is None]),
  "ranking":[[r["id"],(list(r["robust_key"]) if r["robust_key"] else None),r["t_mean"],r["angle_linear"]] for r in h["ranking"]]}
print("rishon",h["id"],h["robust_key"],h["t_mean"],time.time()-t0,flush=True)
json.dump(out,open(sys.argv[2],"w"),indent=1)
