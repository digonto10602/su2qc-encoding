"""Tester 221: are r04-F1-004 and r04-F3-003 the same circuit? gate-by-gate (name, qubits, params) at nominal + 3 pairs; also compare with r03-F3-002 and r02-F1-002."""
import os, json, importlib.util, subprocess
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("c", os.path.join(here, "tester-221-common.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
from su2plaq.rishon.compress.spec import rishon_spec
s0 = rishon_spec("step")
def data(cid, a, b):
    qc = C.build_circuit(cid, s0.with_angles(a, b))
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits), tuple(float(x) for x in i.operation.params)) for i in qc.data], qc.num_qubits
out = {}
for (a, b) in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0), (0.5, 0.3)]:
    d1, n1 = data("r04-F1-004", a, b); d3, n3 = data("r04-F3-003", a, b)
    ok = d1 == d3 and n1 == n3
    # exact compare, and rounded compare
    maxdp = max((abs(x - y) for g1, g3 in zip(d1, d3) for x, y in zip(g1[2], g3[2])), default=0.0) if len(d1) == len(d3) else None
    out[f"{a},{b}"] = dict(len1=len(d1), len3=len(d3), n1=n1, n3=n3, identical_exact=ok, max_param_diff=maxdp,
                           first_diff=next((i for i, (x, y) in enumerate(zip(d1, d3)) if x != y), None))
    print((a, b), out[f"{a},{b}"])
# versus earlier bests (information)
dp, _ = data("r03-F3-002", 0.37, 0.61); d1, _ = data("r04-F1-004", 0.37, 0.61)
out["vs_r03-F3-002"] = dict(len_prev=len(dp), len_new=len(d1))
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), result=out), open(os.path.join(here, "tester-221-samecircuit.json"), "w"), indent=1)
