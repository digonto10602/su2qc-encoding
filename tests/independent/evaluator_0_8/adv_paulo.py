from common import *
from qiskit import qpy
qc = qpy.load(open("/home/digimonk/Projects/su2qc-encoding/refs/paulo/SU2_plaquette_jmax_half_CT.qpy","rb"))[0]
print(qc.num_qubits, [ (r.name, r.size) for r in qc.qregs], dict(qc.count_ops()))
V = enc.target("UB", None, 1.0)
t=time.time()
v = evaluate(qc, enc, V, tol_err=2e-5, tol_leak=1e-9, engine="auto")
print(fmt(v), "acc", v.engine_accuracy, "certified", v.certified, "dropped", v.dropped_total, "wall", time.time()-t)
v2 = evaluate(qc, enc, V, tol_err=1e-10, tol_leak=1e-12, engine="aer_mps") if False else None
json.dump(dict(ok=v.ok, reason=v.reason, err=v.op_norm_error, leak=v.max_leak, dirty=v.dirty_ancilla, engine=v.engine, acc=v.engine_accuracy, certified=v.certified, seconds=v.seconds, gauss=v.gauss_residual), open(OUT+"paulo.json","w"))
V2 = V.conj().T
v3 = evaluate(qc, enc, V2, tol_err=2e-5, tol_leak=1e-9, engine=v.engine); print("inverse:", fmt(v3))
