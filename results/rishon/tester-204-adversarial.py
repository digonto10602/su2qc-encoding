"""Tester 204: perturbed U_B circuits must be rejected by the production verdict."""
import sys, json, copy; sys.path.insert(0,'src')
import numpy as np
import su2plaq.circuits.rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as Vf
enc = RishonEncoding()
base = C.build_UB(0.61)
crx_idx = [i for i, inst in enumerate(base.data) if inst.operation.name == 'crx']
big = max(crx_idx, key=lambda i: abs(base.data[i].operation.params[0]))
def mod(kind, i):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import CRXGate
    if kind == 'beta_sign':
        return C.build_UB(-0.61)
    qc = QuantumCircuit(*base.qregs)
    for k, inst in enumerate(base.data):
        if k == i and kind == 'remove':
            continue
        if k == i:
            th = float(inst.operation.params[0])
            th = -th if kind == 'flip' else th + 1e-6
            qc.append(CRXGate(th), inst.qubits)
        else:
            qc.append(inst.operation, inst.qubits)
    return qc
res = {}
for kind, i in (('flip', crx_idx[3]), ('flip', big), ('plus1e-6', crx_idx[40]), ('plus1e-6', big), ('remove', crx_idx[10]), ('beta_sign', 0)):
    qc = mod(kind, i)
    v = Vf.verify(qc, enc, 'UB', None, 0.61, gauss=False)
    res[f'{kind}@{i}'] = {'ok': v.ok, 'reason': v.reason, 'op_norm_error': v.op_norm_error}
    print(kind, i, res[f'{kind}@{i}'], flush=True)
json.dump(res, open('results/rishon/tester-204-adversarial.json','w'), indent=1)
