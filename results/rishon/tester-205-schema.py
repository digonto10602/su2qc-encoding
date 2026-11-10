import json, glob, math
from su2plaq.results.store import RESULT_KEYS
out={}
for k in ["UE","UE_outer_row","UB","step","step_order2"]:
    t=open(f"results/rishon/{k}.json").read(); d=json.loads(t)
    out[k]=dict(keys_match=list(d)==list(RESULT_KEYS), has_NaN="NaN" in t, has_Infinity="Infinity" in t, nan_paths=[],
                verification_keys=sorted(d["verification"])[:30], prov_keys=sorted(d["provenance"]), git_dirty=d["provenance"]["git_dirty"], commit=d["provenance"]["git_commit"],
                params=d["params"], seeds=d["provenance"]["seeds"], host=d["provenance"]["host"], quick=d["provenance"]["quick"])
    def w(x,p=""):
        if isinstance(x,dict): [w(v,p+"/"+a) for a,v in x.items()]
        elif isinstance(x,list): [w(v,p+f"[{i}]") for i,v in enumerate(x)]
        elif isinstance(x,float) and math.isnan(x): out[k]["nan_paths"].append(p)
    w(d)
    print(k, out[k]["keys_match"], out[k]["has_NaN"], out[k]["nan_paths"][:3], out[k]["git_dirty"], out[k]["commit"])
print("RESULT_KEYS", RESULT_KEYS)
json.dump(out,open("results/rishon/tester-205-schema.json","w"),indent=1)
