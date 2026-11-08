"""Tester 219: are r02-F1-002 and r02-F2-002 the same circuit?  gate-list hash (name, qubits, params) at 3 spec angle pairs + 2 extra, and unordered/commuting comparisons."""
import sys, hashlib, json, importlib.util, os, collections
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("c", os.path.join(here, "tester-219-common.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
from su2plaq.rishon.compress.spec import rishon_spec
s0 = rishon_spec("step")
pairs = [(s0.alpha, s0.beta)] + [tuple(p) for p in s0.alt_angles] + [(2.6, -0.4)]
def gl(qc):
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits), tuple(round(float(x), 12) for x in i.operation.params)) for i in qc.data]
out = {}
for p in pairs:
    a = gl(C.build_circuit("r02-F1-002", s0.with_angles(*p))); b = gl(C.build_circuit("r02-F2-002", s0.with_angles(*p)))
    ha = hashlib.sha256(repr(a).encode()).hexdigest(); hb = hashlib.sha256(repr(b).encode()).hexdigest()
    ca, cb = collections.Counter(a), collections.Counter(b)
    first = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), None)
    nq = (C.build_circuit("r02-F1-002", s0.with_angles(*p)).num_qubits, C.build_circuit("r02-F2-002", s0.with_angles(*p)).num_qubits)
    out[str(p)] = dict(len=(len(a), len(b)), hash_F1=ha[:16], hash_F2=hb[:16], identical_ordered=a == b, multiset_equal=ca == cb, first_diff_index=first,
                       diff_F1_minus_F2=sum((ca - cb).values()), diff_F2_minus_F1=sum((cb - ca).values()), nq=nq, name_counts_F1=dict(collections.Counter(x[0] for x in a)), name_counts_F2=dict(collections.Counter(x[0] for x in b)))
    print(p, out[str(p)]["len"], ha[:12], hb[:12], "ordered-identical", a == b, "multiset", ca == cb, "first diff", first, "nq", nq, flush=True)
    if p == pairs[0] and first is not None:
        print("  F1[first..+3]", a[first:first+3]); print("  F2[first..+3]", b[first:first+3])
json.dump(out, open(os.path.join(here, "tester-219-samecircuit.json"), "w"), indent=1)
