import json, numpy as np
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress.spec import rishon_spec, prune_budget, PRUNE_RATES
from su2plaq.evaluate.evaluator import PRUNE_FRACTION
out = {}
spec = rishon_spec("step")
out["import_seed"] = {s: BL.import_seed(spec, s) for s in ("paulo34","lean22","lean22_v2","spinnet15")}
try:
    BL.import_seed(spec, "nope"); out["unknown"]="no error"
except ValueError as e:
    out["unknown"]="ValueError: "+str(e)
# also kind UE / UB
for k in ("UE","UB"):
    sp = rishon_spec(k)
    out[f"import_{k}"] = {s: BL.import_seed(sp, s)[:60] for s in ("paulo34",)}
# linear_in_angles: check on general UE circuit, step with qiskit_l3
from su2plaq.compress import baselines as LB
for kind in ("UE","step"):
    sp = rishon_spec(kind)
    fn = BL.linear_in_angles(lambda s: BL.general_circuit(s), sp)
    pts = [(0.37,0.61),(0.91,0.23),(1.70,1.00),(0.77,0.13),(2.1,0.4)]
    dev = 0
    for a,b in pts:
        s2 = sp.with_angles(a,b)
        g1 = LB._gate_list(BL.general_circuit(s2)); g2 = LB._gate_list(fn(s2))
        assert [(n,q) for n,_,q in g1]==[(n,q) for n,_,q in g2]
        for (n,p1,_),(n2,p2,_) in zip(g1,g2):
            for x,y in zip(p1,p2): dev=max(dev,abs(x-y))
    out[f"linear_general_{kind}_max_dev_at_5_angle_pairs_incl_2_unfitted"] = dev
# non-linear detection: angle with constant offset
def nonlin(s):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(1); qc.rz(s.alpha+0.3,0); return qc
try:
    BL.linear_in_angles(nonlin, rishon_spec("UE")); out["nonlinear"]="NOT detected"
except ValueError as e:
    out["nonlinear"]="ValueError: "+str(e)
def skel(s):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(1); 
    if s.alpha>1: qc.h(0)
    qc.rz(s.alpha,0); return qc
try:
    BL.linear_in_angles(skel, rishon_spec("UE")); out["skeleton"]="NOT detected"
except ValueError as e:
    out["skeleton"]="ValueError: "+str(e)
# (e) prune budget
cap = PRUNE_FRACTION*spec.tol_err
out["prune"] = {"fraction":PRUNE_FRACTION,"tol_err":spec.tol_err,"cap":cap,"rates":PRUNE_RATES,"cap/ccx":cap/PRUNE_RATES["ccx"],"cap/rccx":cap/PRUNE_RATES["rccx"],"prune_budget":prune_budget(spec)}
print(json.dumps(out, indent=1, default=str))
