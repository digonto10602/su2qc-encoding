import sys, json, math
sys.path.insert(0,'/home/digimonk/Projects/su2qc-encoding/src')
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from su2plaq.metrics.cliffordt import synthesize, pygridsynth_word
from su2plaq.metrics.logical import logical_metrics
rng=np.random.default_rng(20261104)
def opdist(U,V):
    ov=np.trace(V.conj().T@U); ph=ov/abs(ov)
    return np.linalg.norm(U-ph*V,2)
rows=[];bad=0
for case in range(12):
    n=int(rng.integers(2,5)); qc=QuantumCircuit(n)
    nr=0
    while nr<3 or (nr<5 and rng.random()<0.5):
        g=rng.choice(["rz","crz","cp","rx","h","cx","t","ccx"])
        if g=="rz": qc.rz(float(rng.uniform(-3,3)),int(rng.integers(n))); nr+=1
        elif g=="rx": qc.rx(float(rng.uniform(-3,3)),int(rng.integers(n)));nr+=1  # lowers to h rz h ? 
        elif g=="crz": a,b=rng.choice(n,2,replace=False); qc.crz(float(rng.uniform(-3,3)),int(a),int(b)); nr+=2
        elif g=="cp": a,b=rng.choice(n,2,replace=False); qc.cp(float(rng.uniform(-3,3)),int(a),int(b)); nr+=3
        elif g=="h": qc.h(int(rng.integers(n)))
        elif g=="t": qc.t(int(rng.integers(n)))
        elif g=="cx": a,b=rng.choice(n,2,replace=False); qc.cx(int(a),int(b))
        elif g=="ccx" and n>=3: a,b,c=rng.choice(n,3,replace=False); qc.ccx(int(a),int(b),int(c))
    qc.rz(math.pi/4*3,0); qc.rz(math.pi/2,0)  # exact angles in play
    m=logical_metrics(qc)
    for eps in (1e-3,1e-6,1e-9):
        syn,info=synthesize(qc,eps)
        U=Operator(qc).data;V=Operator(syn).data
        d=opdist(U,V)
        tc=syn.count_ops(); tt=tc.get("t",0)+tc.get("tdg",0)
        sum_actual=sum(p["error"] for p in info["per_rotation"])
        ok = d<=info["error_bound_sum"] and info["n_rot"]==m["n_rot"] and tt==m["t_fixed"]+info["t_rot"] and set(tc)<={"cx","h","s","sdg","t","tdg","x","z"}
        # tighter: sum of actual word errors
        ok2 = d<=sum_actual+1e-12
        bad+= (not ok) or (not ok2)
        rows.append(dict(case=case,n=n,eps=eps,n_rot=info["n_rot"],opdist=float(d),sum_eps=info["error_bound_sum"],sum_actual=float(sum_actual),Tcirc=int(tt),Tpred=int(m["t_fixed"]+info["t_rot"]),ok=bool(ok and ok2)))
        print(f"case{case} n={n} eps={eps:g} N_rot={info['n_rot']} opdist={d:.3e} <= sum_actual={sum_actual:.3e} <= sum_eps={info['error_bound_sum']:.1e}; T circ {tt} vs fixed+rot {m['t_fixed']+info['t_rot']}  {'OK' if ok and ok2 else 'FAIL'}")
print("failures",bad,"max ratio opdist/sum_eps",max(r["opdist"]/r["sum_eps"] for r in rows))
json.dump(rows,open("t3.json","w"))
