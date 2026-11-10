import json, time, numpy as np
from qiskit import QuantumCircuit, transpile
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import builder as B, baselines as LB
from su2plaq.compress.metrics import metrics
from su2plaq.compress.spec import get_encoding
from su2plaq.evaluate import sparse_sim as SS
spec = rishon_spec("step")
codes = np.array(get_encoding("rishon").inner_codes(), dtype=np.int64)
print("BASIS", sorted(B.BASIS), "MACROS", sorted(getattr(B,"MACROS",[])))
def l3(extra):
    qc = BL.general_circuit(spec)
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase)
    data = list(qc.data)
    for s0 in range(0, len(data), LB.L3_WINDOW):
        chunk = data[s0:s0+LB.L3_WINDOW]
        qs = sorted({qc.find_bit(q).index for i in chunk for q in i.qubits}); idx={q:k for k,q in enumerate(qs)}
        sub = QuantumCircuit(len(qs))
        for i in chunk: sub.append(i.operation, [idx[qc.find_bit(q).index] for q in i.qubits])
        t = transpile(sub, basis_gates=sorted(B.BASIS)+extra, optimization_level=3, seed_transpiler=12345, qubits_initially_zero=False)
        out.compose(t, qubits=[out.qubits[q] for q in qs], inplace=True)
    return out
res={}
for name, extra in (("L3 basis + ccx,rccx,ch,crx", ["ccx","rccx","ch","crx"]),):
    qc = l3(extra); b = SS.run_batch(qc, codes)
    m = metrics(qc, spec, measured=False)
    print(name, dict(qc.count_ops()), "dropped_total", b.dropped_total, "cx", m["cx"], "t_fixed", m["t_fixed"], flush=True)
