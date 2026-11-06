import sys, time, json
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
import numpy as np
from qiskit import QuantumCircuit
from su2plaq.circuits.twelve import build_UE, build_UB, build_step
from su2plaq.lean import certify as C
from qiskit.quantum_info import Operator

def decrx(qc):
    out = qc.copy_empty_like()
    out.global_phase = qc.global_phase
    for inst in qc.data:
        op = inst.operation; qs = [qc.find_bit(q).index for q in inst.qubits]
        if op.name == "crx":
            th = float(op.params[0]); c, t = qs
            out.h(t); out.rz(th/2, t); out.cx(c, t); out.rz(-th/2, t); out.cx(c, t); out.h(t)
        else:
            out.append(op, [out.qubits[i] for i in qs])
    return out
a, b = 0.37, 0.61
if __name__ == "__main__":
    ub = build_UB(b, with_outer=True)
    print("crx angles / beta:", [float(i.operation.params[0])/b for i in ub.data if i.operation.name=="crx"])
    # sanity: decomposition exact on a small instance
    t = QuantumCircuit(3); t.crx(0.7,0,2); 
    d = decrx(t); print("decrx check:", np.abs(Operator(t).data-Operator(d).data).max())
    enc = C._encoding()
    res = {}
    for kind, order, mk in (("UB",1,lambda: build_UB(b,with_outer=True)), ("step",1,lambda: build_step(a,b,1,with_outer=True)), ("step",2,lambda: build_step(a,b,2,with_outer=True))):
        t0 = time.time()
        qc = decrx(mk())
        r = C.certify_circuit_kind(qc, enc, kind, a, b, order, out_dir="certs")
        res[f"{kind}{order}"] = dict(status=r.status, reason=r.reason[:300], cert=r.cert_path, seconds=round(time.time()-t0,1), n_gates=len(qc.data))
        print(kind, order, res[f"{kind}{order}"], flush=True)
    json.dump(res, open("certs_summary2.json","w"), indent=1)
