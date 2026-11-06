import sys, json, copy, glob
sys.argv = ["x"]
exec(open("hunt.py").read().split("rows = []")[0])   # defs chk
rows = []
def case(name, expect, d, raw=None):
    res, rc, dt = chk(d, name.replace(" ", "_").replace("/", "_").replace("(","").replace(")","")[:60], raw)
    got = "ACCEPT" if res.startswith("ACCEPT") else ("REJECT" if res.startswith("REJECT") else "OTHER")
    ok = got == expect
    rows.append((name, expect, got, ok, res))
    print(("PASS " if ok else "FAIL ") + f"{name:70s} expect {expect:6s} got {got:6s} | {res}", flush=True)
UE = glob.glob("certs/UE-*.json")[0]
base = json.load(open(UE)); base["n_qubits"] = 31   # add three ancillas (28,29,30)
case("UE n_qubits=31 control", "ACCEPT", base)
d = copy.deepcopy(base); d["gates"] += [{"g":"x","q":[30]}]; case("ancilla left dirty (x on ancilla 30)", "REJECT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"x","q":[30]},{"g":"x","q":[30]}]; case("x x on ancilla (identity)", "ACCEPT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"z","q":[30]}]; case("z on clean ancilla (acts as +1)", "ACCEPT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"h","q":[30]}]; case("h on ancilla (dirty superposition)", "REJECT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"cx","q":[3,30]}]; case("cx data->ancilla (entangled garbage)", "REJECT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"cx","q":[3,30]},{"g":"cx","q":[3,30]}]; case("cx data->ancilla twice (uncomputed)", "ACCEPT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"h","q":[30]},{"g":"t","q":[30]},{"g":"cx","q":[3,30]},{"g":"tdg","q":[30]},{"g":"cx","q":[3,30]},{"g":"h","q":[30]}]; case("ancilla phase kickback pattern (net identity? check)", "REJECT", d)
# partial coverage demonstration: wrong circuit = UE + extra p(alpha) on data qubit q; keep only states with no support on q=1 : accepted?
base2 = json.load(open(UE))
q = 4
keep = [k for k, s in enumerate(base2["states"]) if all(((t["code"] >> q) & 1) == 0 for t in s["terms"])]
print("states with no support on q=1 (data qubit 4):", len(keep), "of 433")
wrong = copy.deepcopy(base2); wrong["gates"].append({"g":"p","q":[q],"m":[1,0]})
case("wrong circuit (extra p on q4), full 433 states", "REJECT", wrong)
# restrict
remap = {k:i for i,k in enumerate(keep)}
d = copy.deepcopy(wrong); d["states"] = [dict(copy.deepcopy(base2["states"][k]), k=remap[k]) for k in keep]
blocks = []
for b in base2["target"]["blocks"]:
    if all(k in remap for k in b["ks"]): blocks.append({"ks":[remap[k] for k in b["ks"]], "entries": b["entries"]})
d["target"]["blocks"] = blocks
case(f"wrong circuit, certificate restricted to {len(keep)} states (partial coverage)", "REJECT", d)
