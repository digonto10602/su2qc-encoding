"""Tester 117: own sum T over the 20 E3 pairs vs robust.json cache; nominal vs mean; differences vs r02-F1-002 / r03 parents."""
import json, numpy as np
rc = json.load(open("results/compress/spinnet/robust.json"))["entries"]
ids = ["r04-F1-004","r04-F3-004","r02-F1-002","r03-F1-003","r03-F3-003","r02-F3-002"]
own = {}; out = {}
for e in ids:
    m = json.load(open(f"results/spinnet/tester/4_6_r4/sensb_{e}.json"))["entries"][e]
    T = np.array([x["T"] for x in m]); own[e] = T
    lap = np.array(rc[e]["t_eps"]); d = T - lap
    ent = json.load(open(f"compress/archive/spinnet/entries/{e}.json"))
    out[e] = {"own_sum": int(T.sum()), "cache_sum": int(rc[e]["t_sum"]), "max_abs_pair_diff": int(abs(d).max()), "own_cx": sorted({x["cx"] for x in m}), "cache_cx": rc[e]["cx"],
              "mean": float(T.mean()), "nominal_key_T": ent["key"][1], "angle_linear_cache": rc[e]["angle_linear"], "T_min": int(T.min()), "T_max": int(T.max()), "std": float(T.std(ddof=1))}
    print(e, out[e])
def cmp(a, b):
    D = own[a] - own[b]; print(f"T({a})-T({b}): mean {D.mean():+.2f} sem {D.std(ddof=1)/np.sqrt(20):.2f} min {D.min()} max {D.max()} neg {int((D<0).sum())} zero {int((D==0).sum())} pos {int((D>0).sum())}")
    return {"mean": float(D.mean()), "sem": float(D.std(ddof=1)/np.sqrt(20)), "min": int(D.min()), "max": int(D.max()), "neg": int((D<0).sum()), "zero": int((D==0).sum()), "pos": int((D>0).sum())}
out["cmp"] = {f"{a}-{b}": cmp(a, b) for a, b in [("r04-F1-004","r02-F1-002"),("r04-F1-004","r03-F1-003"),("r04-F3-004","r03-F3-003"),("r04-F3-004","r02-F3-002"),("r04-F3-004","r02-F1-002")]}
json.dump(out, open("results/spinnet/tester/4_6_r4/robust_cmp.json","w"), indent=1)
