import sys, json, time
sys.path.insert(0,'/home/digimonk/Projects/su2qc-encoding/src')
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
nb=json.load(open("/home/digimonk/Projects/su2qc-encoding/refs/paulo/optimized_plaquette_dontcare_lowT.ipynb"))
g={"np":np,"QuantumCircuit":QuantumCircuit,"QuantumRegister":QuantumRegister}
for i in [3,5,7,9,11,13,15,17,19,21,23]:
    exec("".join(nb["cells"][i]["source"]),g)
qc,regs=g["optimized_plaquette_dontcare_low_t"](dt=1.0,gs=1.0,gt=1.0,a=1.0)
print("qubits",qc.num_qubits,"hl ops",dict(qc.count_ops()))
exec("".join(nb["cells"][29]["source"]).split("print")[0] if False else "",g)
c=qc.count_ops(); fixed=4*c.get("rccx",0)+7*c.get("ccx",0)+c.get("t",0)+c.get("tdg",0)
print("notebook fixed structural T estimate:",fixed,"(notebook says 296)")
from su2plaq.metrics.logical import logical_metrics
from su2plaq.metrics.cliffordt import ct_compile, t_table
m=logical_metrics(qc)
print("logical_metrics: cx",m["cx"],"depth",m["depth"],"n_rot",m["n_rot"],"t_fixed",m["t_fixed"],"qubits",m["qubits"],"ancilla",m["ancilla"],m["gates"])
res=[]
for run in range(2):
    t0=time.time(); out,cm=ct_compile(qc,1e-6,3,12345); dt=time.time()-t0
    print(f"run{run}: cx {cm['cx']} T {cm['t']} depth {cm['depth']} qubits {cm['qubits']} gates {cm['gates']} ({dt:.1f}s)")
    res.append(cm)
print("deterministic:",res[0]==res[1])
meta=json.load(open("/home/digimonk/Projects/su2qc-encoding/refs/paulo/SU2_plaquette_jmax_half_CT_metadata.json"))["resources"]
print("Paulo metadata: cx",meta["CX_count"],"T",meta["T_count"],"depth",meta["depth"],"gates",meta["gate_counts"])
json.dump({"mine":res,"paulo":meta,"logical":{k:v for k,v in m.items() if k!="rz_angles"}},open("t4.json","w"),default=str)
rows=t_table(qc,qiskit=True)
for r in rows: print({k:(round(v,1) if isinstance(v,float) else v) for k,v in r.items()})
json.dump(rows,open("t4_table.json","w"))
