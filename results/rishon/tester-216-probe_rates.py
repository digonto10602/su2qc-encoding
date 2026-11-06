import json, time, numpy as np
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress.spec import rishon_spec, PRUNE_RATES
from su2plaq.compress.spec import get_encoding
from su2plaq.evaluate import sparse_sim as SS
codes = np.array(get_encoding("rishon").inner_codes(), dtype=np.int64)
res={}
for kind in ("UB","step"):
    spec = rishon_spec(kind)
    for lad in ("ccx","rccx","mcx"):
        qc = BL.general_circuit(spec, lad)
        c = qc.count_ops()
        t=time.time(); b = SS.run_batch(qc, codes)
        n = {"ccx":c.get("ccx",0),"rccx":c.get("rccx",0)}
        res[f"{kind}/{lad}"] = {"dropped_total":b.dropped_total,"dropped_max":b.dropped_max,"n_ccx":n["ccx"],"n_rccx":n["rccx"],
          "rate_if_pure_ccx": b.dropped_total/max(n["ccx"],1) if lad=="ccx" else None,
          "rate_if_pure_rccx": b.dropped_total/max(n["rccx"],1) if lad=="rccx" else None, "wall":time.time()-t}
        print(kind, lad, res[f"{kind}/{lad}"], flush=True)
json.dump(res, open("/tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/t216/rates.json","w"), indent=1)
