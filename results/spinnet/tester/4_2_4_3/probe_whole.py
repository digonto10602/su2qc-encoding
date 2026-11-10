import time, json
from su2plaq.spinnet import loop as L
from su2plaq.compress import evaluate as E
sp = L.spec(); qc = L._qiskit_l3_whole(L._reference_circuit(sp))
ref = L._reference_circuit(sp)
def gl(q): return [(i.operation.name, tuple(q.find_bit(x).index for x in i.qubits), tuple(round(float(p),9) for p in i.operation.params)) for i in q.data]
t0=time.time(); r = E.evaluate_circuit(qc, sp, "trial")
print(json.dumps({"n_gates_whole": len(qc.data), "n_gates_ref": len(ref.data), "whole_gate_list_equals_ref": gl(qc)==gl(ref), "ops_whole": dict(qc.count_ops()),
 "valid": r.valid, "reason": r.reason, "message": r.message[:300], "wall": time.time()-t0}, default=str))
