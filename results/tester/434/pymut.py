import json, copy, hashlib, pathlib
from su2plaq.rishon import lean_cert as LC
D = pathlib.Path("scratch/t434/pymut"); D.mkdir(exist_ok=True)
base = json.load(open("scratch/t434/UD/UD-o1-8e8b367d09a4.json"))
def run(label, c, rehash=True):
    if rehash: c["gates_sha256"] = hashlib.sha256(json.dumps(c["gates"]).encode()).hexdigest()
    p = D / "m.json"; p.write_text(json.dumps(c)); r = LC.check_inner_certificate(p, timeout=300)
    print(f"{r.status:9s} {label}  [{r.reason[:70]}]"); return (label, r.status, r.reason[:100])
out = []
out.append(run("control", copy.deepcopy(base)))
c = copy.deepcopy(base); c["gates"][5]["g"] = "sx" if c["gates"][5]["g"] != "sx" else "h"; out.append(run("kind swap gate 5", c))
c = copy.deepcopy(base); i = next(i for i, g in enumerate(c["gates"]) if "m" in g); c["gates"][i]["m"][0] += 2; out.append(run("rz exponent +2", c))
c = copy.deepcopy(base); del c["gates"][7]; out.append(run("drop gate 7 (hash updated)", c))
c = copy.deepcopy(base); del c["gates"][7]; out.append(run("drop gate 7 (stale gates_sha256)", c, rehash=False) if False else None)
c = copy.deepcopy(base); c["gates"].append({"g": "x", "q": [3]}); out.append(run("append x data (hash updated)", c))
c = copy.deepcopy(base); c["target"]["entries"][10][2][0][1][0] = "7"; out.append(run("target coeff changed", c))
c = copy.deepcopy(base); c["target"]["kind"] = "UB"; out.append(run("kind UB", c))
c = copy.deepcopy(base); c["states"][3], c["states"][4] = c["states"][4], c["states"][3]; out.append(run("states swapped", c))
c = copy.deepcopy(base); c["phase"]["k"] = ["0", "0", "0", "0", "0", "0", "0", "0"]; out.append(run("phase zero", c))
c = copy.deepcopy(base); c["base"]["d_alpha"] = 3; out.append(run("base 3", c))
c = copy.deepcopy(base); c["schema"] = "x"; out.append(run("schema", c))
c = copy.deepcopy(base); c["gates"].append({"g": "x", "q": [3]}); out.append(run("append x, STALE gates_sha256", c, rehash=False))
json.dump([o for o in out if o], open("results/tester/434-pymut.json", "w"), indent=1)
