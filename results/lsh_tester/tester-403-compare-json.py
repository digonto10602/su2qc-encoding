import json, warnings
warnings.filterwarnings("ignore")
import pygridsynth as pg
from qiskit import QuantumCircuit
import su2plaq.circuits.spinnet as CS
from su2plaq.circuits.lsh import wrap_spinnet
def cnt(qc):
    q = qc.decompose(gates_to_decompose=['rccx'])
    cx=t=0; angs=[]
    for i in q.data:
        n=i.operation.name
        if n=='cx': cx+=1
        elif n in('t','tdg'): t+=1
        elif n in ('rz','p'): angs.append(float(i.operation.params[0]))
    return cx,t,angs
def tsyn(angs,eps): return sum(str(pg.gridsynth_gates(theta=a,epsilon=eps)).count('T') for a in angs)
rec = json.load(open("results/lsh_tester/tester-403-recount.json"))
res = {}
for r in rec["rows"][:3]:
    d = json.load(open(f"results/lsh/{r['file']}.json"))
    tt = {str(e["eps"]): e["t_total"] for e in d["metrics"]["t_table"]}
    lg = d["metrics"]["logical"]
    ok = lg["cx"]==r["cx"] and lg["t_fixed"]==r["t_fixed"] and lg["n_rot"]==r["n_rot"] and all(tt[k]==v for k,v in r["T_eps"].items())
    print(r["file"], "json", lg, tt, "recount", r["cx"], r["t_fixed"], r["n_rot"], r["T_eps"], "MATCH" if ok else "MISMATCH")
    res[r["file"]]=ok
# wrapped rows
d = json.load(open("results/lsh/UB.json"))
for name in ["general7","pairs9","flags4","flags5","flags6"]:
    sn = CS.build_UB(0.61) if name=="general7" else CS.trotter_v2_circuit(name,0.61)
    w = wrap_spinnet(sn)
    cx,t,angs = cnt(w); T6 = t+tsyn(angs,1e-6)
    js = d["extra"]["comparison"]["wrapped_spinnet"][name]
    print(name, "recount cx/rot/tfix/T1e-6:", cx,len(angs),t,T6, "| json:", js["logical"]["cx"], js["logical"]["n_rot"], js["logical"]["t_fixed"], js["t_table_pygridsynth"][0]["t_total"], "| spinnet alone", cnt(sn)[:2])
print(list(d["extra"]["comparison"].keys()))
for k,v in d["extra"]["comparison"].items():
    if k!="wrapped_spinnet": print(k, json.dumps(v)[:600])
