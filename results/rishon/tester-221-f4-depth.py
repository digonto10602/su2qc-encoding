"""Tester 221: F4-004 claims 'lowering the depth at equal CX and T' vs parent r03-F4-003: gate multiset, QuantumCircuit depth, depth_CT (production metrics) at nominal."""
import os, collections, importlib.util, json
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("c", os.path.join(here, "tester-221-common.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress.metrics import metrics
s0 = rishon_spec("step"); out = {}
for cid in ("r03-F4-003", "r04-F4-004"):
    qc = C.build_circuit(cid, s0)
    m = metrics(qc, s0, measured=True)
    out[cid] = dict(n_gates=len(qc.data), gates=dict(collections.Counter(i.operation.name for i in qc.data)), depth_macro=qc.depth(), depth_ct=m['depth_ct'], cx=m['cx'], t_eps=m['t_eps'])
    print(cid, out[cid])
a, b = [[(i.operation.name, tuple(q._index if hasattr(q,'_index') else 0 for q in i.qubits)) for i in C.build_circuit(c, s0).data] for c in out]
out['same_gate_multiset_names'] = out['r03-F4-003']['gates'] == out['r04-F4-004']['gates']
print('same gate-name multiset', out['same_gate_multiset_names'])
json.dump(out, open(os.path.join(here, "tester-221-f4-depth.json"), "w"), indent=1)
