import json, numpy as np
from qiskit import QuantumCircuit
from su2plaq.compress.spec import get_encoding
import su2plaq.rishon.compress  # noqa
from su2plaq.evaluate import sparse_sim as SS
codes = np.array(get_encoding("rishon").inner_codes(), dtype=np.int64)
rng = np.random.default_rng(216)
def circ(kind, n):
    qc = QuantumCircuit(26)         # 16 data + 10 ancillas
    for _ in range(n):
        a,b = rng.choice(16, 2, replace=False); t = 16 + int(rng.integers(0,10))
        (qc.ccx if kind=="ccx" else qc.rccx)(int(a), int(b), t)
        (qc.ccx if kind=="ccx" else qc.rccx)(int(a), int(b), t)   # compute/uncompute so ancillas return to 0
    return qc
out={}
for kind,n in (("ccx",2350),("rccx",350),("rccx",700)):
    qc = circ(kind,n); b = SS.run_batch(qc, codes)
    ops,_ = SS._translate(qc); nb = sum(1 for o in ops if o[0] in SS._BRANCH)
    out[f"{kind}x{2*n}"] = {"gates": 2*n, "branching_after_lowering": nb, "dropped_total": b.dropped_total}
    print(kind, 2*n, "branching", nb, "dropped_total", b.dropped_total, "(cap 1e-12)", flush=True)
json.dump(out, open("/home/digonto/Projects/su2qc-rishon/results/rishon/tester-216-native-ccx-probe.json","w"), indent=1)
