"""Tester 118: own per-pair T (robust_depth_*.json in 4_6_r4/4_6_r5, sensb for r03-F3/r02-F3) vs robust.json cache; paired differences over the 20 pairs."""
import json, numpy as np
rc = json.load(open("results/compress/spinnet/robust.json"))["entries"]
own = {}; D = "results/spinnet/tester/"
for e in ("r05-F1-005", "r05-F2-005", "r05-F3-005", "r02-F1-002"): own[e] = json.load(open(D + f"4_6_r5/robust_depth_{e}.json"))[e]["T"]
for e in ("r03-F1-003", "r03-F2-003", "r04-F1-004", "r04-F3-004"): own[e] = json.load(open(D + f"4_6_r4/robust_depth_{e}.json"))[e]["T"]
for e in ("r03-F3-003",): own[e] = [x["T"] for x in json.load(open(D + f"4_6_r4/sensb_{e}.json"))["entries"][e]]
own = {e: np.array(v) for e, v in own.items()}; res = {}
for e, T in own.items():
    lap = np.array(rc[e]["t_eps"]); ent = json.load(open(f"compress/archive/spinnet/entries/{e}.json"))
    res[e] = {"own_sum": int(T.sum()), "cache_sum": int(rc[e]["t_sum"]), "max_abs_pair_diff": int(abs(T - lap).max()), "mean": float(T.mean()), "std": float(T.std(ddof=1)), "min": int(T.min()), "max": int(T.max()), "nominal_T_key": ent["key"][1], "nominal_minus_mean": float(ent["key"][1] - T.mean())}
    print(e, res[e])
def cmp(a, b):
    d = own[a] - own[b]; r = {"mean": float(d.mean()), "sem": float(d.std(ddof=1) / np.sqrt(20)), "min": int(d.min()), "max": int(d.max()), "neg": int((d < 0).sum()), "zero": int((d == 0).sum()), "pos": int((d > 0).sum())}
    print(f"T({a})-T({b}): " + ", ".join(f"{k} {v:.2f}" if isinstance(v, float) else f"{k} {v}" for k, v in r.items())); return r
res["cmp"] = {f"{a}-{b}": cmp(a, b) for a, b in [("r05-F2-005", "r02-F1-002"), ("r05-F2-005", "r03-F2-003"), ("r05-F3-005", "r04-F3-004"), ("r05-F3-005", "r03-F3-003"), ("r05-F1-005", "r04-F1-004"), ("r05-F1-005", "r05-F3-005"), ("r05-F3-005", "r02-F1-002"), ("r05-F1-005", "r02-F1-002")]}
json.dump(res, open(D + "4_6_r5/robust_cmp.json", "w"), indent=1)
