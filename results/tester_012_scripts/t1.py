import sys, json, math
sys.path.insert(0,'/home/digimonk/Projects/su2qc-encoding/src')
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from su2plaq.metrics.logical import logical_metrics, LOGICAL_BASIS, SEED
rng = np.random.default_rng(20261104)
out = {"commit":"803d56a-dirty","seed":20261104}
# (1) random circuits
gates1 = ["h","s","sdg","t","tdg","x","z","y","rz","p","rx","ry"]
def rand_circ(n, depth, rng):
    qc = QuantumCircuit(n)
    names = ["h","s","sdg","t","tdg","x","z","rz","p","cx","cz","swap","ccx","rccx","ch","crz","crx","cp","ccz","cry"]
    for _ in range(depth):
        g = names[rng.integers(len(names))]
        ar = {"h":1,"s":1,"sdg":1,"t":1,"tdg":1,"x":1,"z":1,"rz":1,"p":1,"cx":2,"cz":2,"swap":2,"ccx":3,"rccx":3,"ch":2,"crz":2,"crx":2,"cp":2,"ccz":3,"cry":2}[g]
        qs = list(rng.choice(n, ar, replace=False))
        if g in ("rz","p","crz","crx","cp","cry"):
            # sometimes Clifford+T multiples of pi/4
            th = float(rng.uniform(-3,3)) if rng.random()<0.7 else float(rng.integers(-8,9))*math.pi/4
            getattr(qc,g)(th,*qs)
        else:
            getattr(qc,g)(*qs)
    return qc
rows=[]; bad=0
for s in range(30):
    n = int(rng.integers(3,6)); qc = rand_circ(n, int(rng.integers(8,25)), rng)
    m = logical_metrics(qc)
    low = transpile(qc, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED)
    ops = low.count_ops()
    # independent angle classification
    nrot=0; tf=ops.get("t",0)+ops.get("tdg",0)
    for ins in low.data:
        if ins.operation.name=="rz":
            k = ins.operation.params[0]/(math.pi/4)
            if abs(k-round(k))<1e-9:
                tf += int(round(k))%2
            else: nrot+=1
    ref = {"cx":ops.get("cx",0),"depth":low.depth(),"n_rot":nrot,"t_fixed":tf}
    got = {k:m[k] for k in ref}
    # unitary equivalence of lowering (global phase)
    U=Operator(qc).data; V=Operator(low).data
    ov=np.trace(V.conj().T@U); uerr=np.linalg.norm(U-ov/abs(ov)*V,2)
    ok = ref==got and uerr<1e-10 and m["gates"]==dict(ops)
    bad += (not ok)
    rows.append({"seed_idx":s,"n":n,"ref":ref,"got":got,"unitary_err":float(uerr),"ok":ok,"ops_in":dict(qc.count_ops())})
print("random circuits:",len(rows),"mismatches:",bad,"max unitary err",max(r["unitary_err"] for r in rows))
covered=set()
for r in rows: covered|=set(r["ops_in"])
print("gates covered:",sorted(covered))
out["random"]=rows
# macro table measured
macro={}
th=0.37
def mk(name):
    if name=="ccx": q=QuantumCircuit(3); q.ccx(0,1,2)
    elif name=="rccx": q=QuantumCircuit(3); q.rccx(0,1,2)
    elif name=="ccz": q=QuantumCircuit(3); q.ccz(0,1,2)
    elif name=="swap": q=QuantumCircuit(2); q.swap(0,1)
    elif name=="ch": q=QuantumCircuit(2); q.ch(0,1)
    elif name=="crz": q=QuantumCircuit(2); q.crz(th,0,1)
    elif name=="crx": q=QuantumCircuit(2); q.crx(th,0,1)
    elif name=="cp": q=QuantumCircuit(2); q.cp(th,0,1)
    elif name=="cz": q=QuantumCircuit(2); q.cz(0,1)
    return q
table={"ccx":(6,7,0),"rccx":(3,4,0),"ccz":(6,7,0),"swap":(3,0,0),"ch":(1,2,0),"crz":(2,0,2),"crx":(2,0,2),"cp":(2,0,3),"cz":(1,0,0)}
for k,v in table.items():
    q=mk(k); m=logical_metrics(q)
    low=transpile(q,basis_gates=LOGICAL_BASIS,optimization_level=0,seed_transpiler=SEED)
    U=Operator(q).data;V=Operator(low).data; ov=np.trace(V.conj().T@U)
    macro[k]={"expected":v,"got":(m["cx"],m["t_fixed"],m["n_rot"]),"depth":m["depth"],"unitary_err":float(np.linalg.norm(U-ov/abs(ov)*V,2)),"gates":m["gates"]}
    print(k,v,macro[k]["got"],"depth",m["depth"],"uerr %.1e"%macro[k]["unitary_err"], m["gates"])
out["macro"]=macro
json.dump(out,open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/t1.json","w"),default=str)
