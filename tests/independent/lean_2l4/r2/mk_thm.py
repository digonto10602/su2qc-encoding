import sys, json, copy, os
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import certify as C
S = "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/r2/"
base = json.load(open(S + "embedded.json"))
os.makedirs(S + "thm", exist_ok=True)
G = base["gates"]
def blk_of(k):
    for b in base["target"]["blocks"]:
        if k in b["ks"]: return b
size2 = next(b for b in base["target"]["blocks"] if len(b["ks"]) == 2)
size1 = next(b for b in base["target"]["blocks"] if len(b["ks"]) == 1)
muts = {}
d = copy.deepcopy(base); d["gates"][0]["m"] = [-2, 0]; muts["angle"] = d
d = copy.deepcopy(base); d["gates"].append({"g": "z", "q": [3]}); muts["extraZ"] = d
# first adjacent non-identical pair: swap gates 4 and 5 (cx[8,7] and cx[8,6] commute) -> pick h/t pair
i = next(i for i in range(len(G)-1) if G[i]["g"] == "h" and G[i+1]["g"] == "t")
d = copy.deepcopy(base); d["gates"][i], d["gates"][i+1] = d["gates"][i+1], d["gates"][i]; muts["swap"] = d
d = copy.deepcopy(base); d["phase"]["m"] = [1, 0]; muts["phase"] = d
d = copy.deepcopy(base); d["gates"].append({"g": "x", "q": [45]}); muts["dirty"] = d
d = copy.deepcopy(base); d["states"] = d["states"][:-1]; d["target"]["blocks"] = [b for b in d["target"]["blocks"] if 432 not in b["ks"]]; muts["subset"] = d
d = copy.deepcopy(base); d["states"][10]["k"] = 11; muts["dupidx"] = d
d = copy.deepcopy(base); d["states"][5]["terms"][0]["c"][0] = "7/5"; muts["coef"] = d
d = copy.deepcopy(base); d["states"][5]["terms"].pop(); muts["term_deleted"] = d
k2 = size2["ks"][0]; k1 = size1["ks"][0]
def neg(c): return [("-" + x if x not in ("0",) and not x.startswith("-") else (x[1:] if x.startswith("-") else x)) for x in c]
d = copy.deepcopy(base)
for t in d["states"][k2]["terms"]: t["c"] = neg(t["c"])
muts["signflip_block2"] = d
d = copy.deepcopy(base)
for t in d["states"][k1]["terms"]: t["c"] = neg(t["c"])
muts["signflip_block1"] = d
d = copy.deepcopy(base); d["target"]["blocks"][0]["entries"][0][2][0][0][0] += 1; muts["target"] = d
d = copy.deepcopy(base); d["states"][0]["terms"][0]["code"] ^= 4; muts["stateterm"] = d
for name, d in muts.items():
    open(S + f"thm/{name}.json", "w").write(json.dumps(d, separators=(",", ":")))
    C.write_theorem_file(S + f"thm/{name}.json", "gen_step_ok", S + f"thm/{name}.lean")
print(list(muts), "size2 block state", k2, "size1", k1)
# name limit
for nm in ("gen_step_ok", "a" * 13, "a" * 14, "bad name", "x.y"):
    try:
        C.write_theorem_file(S + "thm/angle.json", nm, S + "thm/_n.lean"); print("name", repr(nm), len(nm), "-> accepted")
    except ValueError as e:
        print("name", repr(nm), len(nm), "-> ValueError")
