import sys, json, copy, glob, random, subprocess, os, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
EXE = "/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert"
os.makedirs("mutub", exist_ok=True)
UB = glob.glob("certs/UB-*.json")[0]
base = json.load(open(UB))
G = base["gates"]; print("n gates", len(G), "n_qubits", base["n_qubits"])
random.seed(11)
def commute(g1, g2):
    qs = sorted(set(g1["q"]) | set(g2["q"])); idx = {q:i for i,q in enumerate(qs)}
    def mat(g):
        qc = QuantumCircuit(len(qs)); m = g.get("m",[0,0]); 
        th = m[0]*0.37/base["base"]["d_alpha"] + m[1]*0.61/base["base"]["d_beta"]
        qq = [idx[q] for q in g["q"]]
        if g["g"] in ("rz","p"): getattr(qc,g["g"])(th,*qq)
        elif g["g"]=="cp": qc.cp(th,*qq)
        else: getattr(qc,g["g"])(*qq)
        return Operator(qc).data
    A, B = mat(g1), mat(g2)
    return np.allclose(A@B, B@A)
muts = []
# adjacent swaps of non-commuting gates
cnt = 0
idxs = list(range(len(G)-1)); random.shuffle(idxs)
for i in idxs:
    if not commute(G[i], G[i+1]):
        d = copy.deepcopy(base); d["gates"][i], d["gates"][i+1] = d["gates"][i+1], d["gates"][i]
        muts.append((f"swap non-commuting adjacent gates {i},{i+1} ({G[i]['g']}{G[i]['q']},{G[i+1]['g']}{G[i+1]['q']})", "REJECT", d)); cnt += 1
        if cnt == 5: break
cnt = 0
for i in idxs:
    if commute(G[i], G[i+1]) and G[i] != G[i+1]:
        d = copy.deepcopy(base); d["gates"][i], d["gates"][i+1] = d["gates"][i+1], d["gates"][i]
        muts.append((f"swap COMMUTING adjacent gates {i},{i+1} (control)", "ACCEPT", d)); cnt += 1
        if cnt == 2: break
# missing gates
for i in random.sample(range(len(G)), 4):
    d = copy.deepcopy(base); d["gates"].pop(i); muts.append((f"missing gate {i} ({G[i]['g']}{G[i]['q']})", "REJECT", d))
# extra Z on data/outer/clean ancilla etc
d = copy.deepcopy(base); d["gates"].append({"g":"z","q":[3]}); muts.append(("extra Z data q3", "REJECT", d))
d = copy.deepcopy(base); d["gates"].insert(len(G)//2, {"g":"z","q":[7]}); muts.append(("extra Z mid-circuit data q7", "REJECT", d))
d = copy.deepcopy(base); d["gates"].append({"g":"x","q":[40]}); muts.append(("ancilla 40 left dirty", "REJECT", d))
d = copy.deepcopy(base); d["gates"].insert(len(G)//2, {"g":"x","q":[40]}); muts.append(("ancilla flipped mid-circuit never restored", "REJECT", d))
# angle multiples
rzs = [i for i,g in enumerate(G) if g["g"] in ("rz","p","cp")]
print("angle gates:", [(i, G[i]["g"], G[i]["m"]) for i in rzs])
for i in rzs[:3]:
    for new in ([G[i]["m"][0]*2 if G[i]["g"]!="rz" else G[i]["m"][0]*2, G[i]["m"][1]], [-G[i]["m"][0], -G[i]["m"][1]], [G[i]["m"][0]+ (2 if G[i]["g"]=="rz" else 1), G[i]["m"][1]]):
        d = copy.deepcopy(base); d["gates"][i]["m"] = new; muts.append((f"gate {i} angle {G[i]['m']} -> {new}", "REJECT", d))
# phases
d = copy.deepcopy(base); d["phase"]["m"] = [base["phase"]["m"][0]+1, base["phase"]["m"][1]]; muts.append(("phase exponent alpha+1", "REJECT", d))
d = copy.deepcopy(base); d["phase"]["m"] = [base["phase"]["m"][0], base["phase"]["m"][1]+1]; muts.append(("phase exponent beta+1", "REJECT", d))
print("base phase:", base["phase"])
# target from other kind: UE target vs UB circuit
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import exact as E
for kind, order in (("UE",1),("step",1)):
    d = copy.deepcopy(base); bl = E.exact_target_blocks(kind, order)
    d["target"] = {"kind": kind, "order": order, "blocks": [{"ks": b["ks"], "entries": [[i,j,lp.to_json()] for i,j,lp in b["entries"]]} for b in bl]}
    muts.append((f"UB circuit vs {kind} target", "REJECT", d))
# state term moved
d = copy.deepcopy(base); d["states"][100]["terms"][0]["code"] ^= 1; muts.append(("state term moved", "REJECT", d))
# wrong claimed target: UB with beta -> -beta  (conj exponent)
d = copy.deepcopy(base)
for b in d["target"]["blocks"]:
    for e in b["entries"]:
        for t in e[2]: t[0][1] = -t[0][1]
muts.append(("target with z_beta -> 1/z_beta (U_B(-beta))", "REJECT", d))
def run(i):
    name, exp, d = muts[i]; p = f"mutub/{i}.json"; json.dump(d, open(p,"w")); t=time.time()
    r = subprocess.run([EXE, "check", p], capture_output=True, text=True, timeout=1500)
    out = r.stdout.strip().splitlines()[0] if r.stdout.strip() else "<empty>"
    got = "ACCEPT" if out.startswith("ACCEPT") else "REJECT" if out.startswith("REJECT") else "OTHER"
    return name, exp, got, out[:90], time.time()-t
res = []
with ThreadPoolExecutor(4) as ex:
    for r in ex.map(run, range(len(muts))):
        ok = r[1]==r[2]; res.append(dict(name=r[0], expect=r[1], got=r[2], ok=ok, out=r[3], sec=round(r[4],1)))
        print(("PASS " if ok else "FAIL ") + f"{r[0]:75s} expect {r[1]} got {r[2]} | {r[3]} ({r[4]:.0f}s)", flush=True)
json.dump(res, open("hunt_UB.json","w"), indent=1)
print(sum(r["ok"] for r in res), "/", len(res))
