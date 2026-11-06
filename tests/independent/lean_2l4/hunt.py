import sys, json, copy, subprocess, glob, random, os, time
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import exact as E
EXE = "/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert"
os.makedirs("mut", exist_ok=True)
def chk(d, tag, raw=None):
    p = f"mut/{tag}.json"
    if raw is not None: open(p, "w").write(raw)
    else: json.dump(d, open(p, "w"))
    t = time.time()
    r = subprocess.run([EXE, "check", p], capture_output=True, text=True, timeout=900)
    out = r.stdout.strip().splitlines()[0] if r.stdout.strip() else "<empty>"
    err = (" [stderr: " + r.stderr.strip()[:120].replace("\n"," ") + "]") if r.stderr.strip() else ""
    return out[:110] + err, r.returncode, time.time()-t
rows = []
def case(name, expect, d, raw=None):
    res, rc, dt = chk(d, name.replace(" ", "_").replace("/", "_")[:60], raw)
    got = "ACCEPT" if res.startswith("ACCEPT") else ("REJECT" if res.startswith("REJECT") else "OTHER")
    ok = (got == expect) or (expect == "REJECT" and got == "OTHER")
    rows.append((name, expect, got, ok, res))
    print(("PASS " if ok else "FAIL ") + f"{name:62s} expect {expect:6s} got {got:6s} | {res}  ({dt:.1f}s)", flush=True)
def load(p): return json.load(open(p))
UE = glob.glob("certs/UE-*.json")[0]
UBs = glob.glob("certs/UB-*.json")
base = load(UE)
case("UE baseline", "ACCEPT", base)
# 1 wrong angle multiple
for new in ([-2,0],[-4,0],[3,0],[-3,1],[0,-3],[-3,0.0]):
    d = copy.deepcopy(base); d["gates"][1]["m"] = new
    case(f"UE gate1 angle m={new}", "REJECT", d)
# swapped gate order of commuting gates (control: must stay ACCEPT)
d = copy.deepcopy(base); d["gates"][0], d["gates"][1] = d["gates"][1], d["gates"][0]
case("UE swap two commuting p gates (control)", "ACCEPT", d)
# missing gate, extra Z, extra gates
d = copy.deepcopy(base); d["gates"].pop(2); case("UE missing gate", "REJECT", d)
d = copy.deepcopy(base); d["gates"].append({"g":"z","q":[3]}); case("UE extra Z data qubit", "REJECT", d)
d = copy.deepcopy(base); d["gates"].append({"g":"z","q":[20]}); case("UE extra Z on outer qubit (acts as sign on outer states)", "REJECT", d)
d = copy.deepcopy(base); d["gates"].append({"g":"z","q":[30]}); case("UE extra Z on ancilla (|0> eigenvalue +1 -> physically trivial)", "ACCEPT", d)
d = copy.deepcopy(base); d["gates"].append({"g":"x","q":[30]}); case("UE ancilla left dirty (x on ancilla)", "REJECT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"x","q":[30]},{"g":"x","q":[30]}]; case("UE x x on ancilla (identity; control)", "ACCEPT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"h","q":[30]},{"g":"h","q":[30]}]; case("UE h h on ancilla (identity; control)", "ACCEPT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"t","q":[2]}]; case("UE extra T on data", "REJECT", d)
d = copy.deepcopy(base); d["gates"] += [{"g":"p","q":[2],"m":[1,0]}]; case("UE extra p(theta) on data (any angle)", "REJECT", d)
# wrong phase
for ph, mm in ((None, [1,0]), (None, [0,1]), (None, [-1, 0])):
    d = copy.deepcopy(base); d["phase"]["m"] = mm; case(f"UE phase exponent {mm}", "REJECT", d)
d = copy.deepcopy(base); d["phase"]["k"] = (E.omega_power(1)).to_json(); case("UE phase k=omega", "REJECT", d)
d = copy.deepcopy(base); d["phase"]["k"] = (E.KNum(-1)).to_json(); case("UE phase k=-1", "REJECT", d)
d = copy.deepcopy(base); d["phase"]["k"] = (E.KNum(2)).to_json(); case("UE phase k=2 (|c|!=1)", "REJECT", d)
# state tampering
d = copy.deepcopy(base); d["states"][5]["terms"][0]["code"] ^= 4; case("state term moved (code ^= 4)", "REJECT", d)
d = copy.deepcopy(base); d["states"][5]["terms"][0]["c"][0] = "7/5"; case("state coefficient altered", "REJECT", d)
d = copy.deepcopy(base); d["states"][5]["terms"].pop(); case("state term deleted", "REJECT", d)
d = copy.deepcopy(base); d["states"][5]["terms"].append(copy.deepcopy(d["states"][5]["terms"][0])); case("state term duplicated (same code)", "REJECT", d)
# state swapped: states k, l swapped contents
d = copy.deepcopy(base); a,b = d["states"][3]["terms"], d["states"][200]["terms"]; d["states"][3]["terms"], d["states"][200]["terms"] = b, a
case("two states swapped contents", "REJECT", d)
# target tamper
d = copy.deepcopy(base); d["target"]["blocks"][0]["entries"][0][2][0][0][0] += 1; case("target exponent changed", "REJECT", d)
d = copy.deepcopy(base); d["target"]["blocks"][0]["entries"][0][2][0][1][0] = "2"; case("target coefficient changed", "REJECT", d)
d = copy.deepcopy(base); d["target"]["blocks"][3]["entries"] = []; case("target entry removed (V column zero)", "REJECT", d)
# target from another kind
for kind, order in (("UB",1),("step",1)):
    d = copy.deepcopy(base); dA, dB = E.target_base(kind, order)
    bl = E.exact_target_blocks(kind, order)
    d["target"] = {"kind": kind, "order": order, "blocks": [{"ks": b["ks"], "entries": [[i,j,lp.to_json()] for i,j,lp in b["entries"]]} for b in bl]}
    case(f"UE circuit vs {kind} target", "REJECT", d)
# duplicated / uncovered states
d = copy.deepcopy(base); d["target"]["blocks"][1]["ks"] = d["target"]["blocks"][0]["ks"]; case("two blocks cover the same state", "REJECT", d)
d = copy.deepcopy(base); d["target"]["blocks"].pop(); case("last block missing (uncovered state)", "REJECT", d)
d = copy.deepcopy(base); d["target"]["blocks"][0]["ks"] = [999]; case("block refers to nonexistent state", "REJECT", d)
d = copy.deepcopy(base); d["states"][10]["k"] = 11; case("states list duplicated index k (hole)", "REJECT", d)
d = copy.deepcopy(base); d["states"] = d["states"][:-1]; case("last state dropped from states (block still refers)", "REJECT", d)
# drop state AND its block together -> checker accepts partial coverage?
d = copy.deepcopy(base); d["states"] = d["states"][:-1]; d["target"]["blocks"] = [b for b in d["target"]["blocks"] if 432 not in b["ks"]]; case("[note] last state + its block both dropped (partial coverage)", "REJECT", d)
d = copy.deepcopy(base); d["states"] = []; d["target"]["blocks"] = []; case("empty states", "REJECT", d)
d = copy.deepcopy(base); d["target"]["blocks"][0]["entries"][0][0] = 5; case("[note] target entry row index out of block range (ks[5]!)", "REJECT", d)
# range / structure
for g, nm in (({"g":"cx","q":[0,99]},"cx qubit 99"), ({"g":"cx","q":[0,0]},"cx repeated qubit"), ({"g":"cx","q":[-1,0]},"negative qubit"),
              ({"g":"cx","q":[0]},"cx arity 1"), ({"g":"h","q":[0,1]},"h arity 2"), ({"g":"ccx","q":[0,1,1]},"ccx repeated"),
              ({"g":"foo","q":[0]},"unknown gate"), ({"g":"rz","q":[0],"m":[1,0]},"rz odd exponent"), ({"g":"h","q":[0],"m":[1,0]},"h with angle"),
              ({"g":"cx","q":[0,62]},"cx qubit 62 (n=44? n_qubits)"), ({"g":"cx","q":[0,1.5]},"qubit 1.5"), ({"g":"cx","q":["a",1]},"qubit string"), ({"g":"x"},"missing q"), ({"q":[0]},"missing g")):
    d = copy.deepcopy(base); d["gates"].append(g); case("malformed gate: " + nm, "REJECT", d)
# huge exponents
d = copy.deepcopy(base); d["gates"][0]["m"] = [10**30, 0]; case("huge exponent 1e30 on gate", "REJECT", d)
d = copy.deepcopy(base); d["gates"][0]["m"] = [10**30, 10**30]; d["gates"][1]["m"] = [-10**30, -10**30]; case("huge exponents (cancelling 1e30; should REJECT since != target)", "REJECT", d)
d = copy.deepcopy(base); d["phase"]["m"] = [10**40, 0]; case("huge phase exponent", "REJECT", d)
d = copy.deepcopy(base); d["n_qubits"] = 10**9; case("n_qubits = 1e9", "REJECT", d)
d = copy.deepcopy(base); d["n_qubits"] = 63; case("n_qubits = 63", "REJECT", d)
d = copy.deepcopy(base); d["n_qubits"] = 44; case("n_qubits = 44 (correct; control)", "ACCEPT", d)
print("n_qubits in base:", base["n_qubits"], base["n_data"], base["n_outer"])
d = copy.deepcopy(base); d["n_qubits"] = 20; case("n_qubits too small", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["code"] = 2**70; case("state code 2^70", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["code"] = 2**30; case("state code on ancilla 2^30", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["c"] = ["1/0"]+["0"]*7; case("zero denominator", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["c"] = ["abc"]+["0"]*7; case("non-numeric rational", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["c"] = ["1"]*7; case("K with 7 components", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["c"] = ["1.5"]+["0"]*7; case("decimal rational 1.5", "REJECT", d)
d = copy.deepcopy(base); d["states"][0]["terms"][0]["c"] = ["2/4"]+["0"]*7; case("unreduced rational 2/4 (control: value same as 1/2)", "ACCEPT" if base["states"][0]["terms"][0]["c"][0] == "1/2" else "REJECT", d)
d = copy.deepcopy(base); d["schema"] = "su2plaq-cert-2"; case("wrong schema", "REJECT", d)
d = copy.deepcopy(base); del d["target"]; case("no target", "REJECT", d)
d = copy.deepcopy(base); del d["phase"]; case("no phase (default c=1; UE phase is 1 -> ACCEPT)", "ACCEPT" if base["phase"]["m"]==[0,0] and base["phase"]["k"][0]=="1" else "REJECT", d)
d = copy.deepcopy(base); del d["states"]; case("no states", "REJECT", d)
d = copy.deepcopy(base); del d["gates"]; case("no gates key", "REJECT", d)
d = copy.deepcopy(base); d["gates"] = []; case("empty gate list (identity)", "REJECT", d)
raw = open(UE).read()
case("truncated JSON", "REJECT", None, raw=raw[:len(raw)//2])
case("empty file", "REJECT", None, raw="")
case("not json", "REJECT", None, raw="hello")
case("json null", "REJECT", None, raw="null")
case("json []", "REJECT", None, raw="[]")
print("\nFAILS:", [r for r in rows if not r[3]])
json.dump([dict(name=r[0], expect=r[1], got=r[2], ok=r[3], out=r[4]) for r in rows], open("hunt_UE.json","w"), indent=1)
print(f"{sum(r[3] for r in rows)}/{len(rows)} as expected")
