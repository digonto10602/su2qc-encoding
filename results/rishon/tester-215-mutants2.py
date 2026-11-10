"""Tester 215 probe (a) extra: control changes on cx / cz / ch (data-only errors), full mode, general step circuit; seed 215."""
import json, subprocess, time
import numpy as np
from qiskit.circuit import CircuitInstruction
import su2plaq.rishon.compress as RC
from su2plaq.rishon.compress import spec as S, baselines as BL, evaluate as EV
spec = S.rishon_spec("step"); qc0 = BL.general_circuit(spec); rng = np.random.default_rng(215)
rows = []
for name in ("cx", "cz", "ch", "cx"):
    ix = [i for i, x in enumerate(qc0.data) if x.operation.name == name and all(qc0.find_bit(q).index < 16 for q in x.qubits)]
    i = int(rng.choice(ix)); qs = list(qc0.data[i].qubits); idx = [qc0.find_bit(q).index for q in qs]
    new = int(rng.choice([j for j in range(16) if j not in idx])); q = qc0.copy()
    q.data[i] = CircuitInstruction(q.data[i].operation, [qc0.qubits[new]] + qs[1:], q.data[i].clbits)
    t = time.time(); r = EV.evaluate_circuit(q, spec, mode="full")
    row = dict(gate=name, index=i, qubits=idx, new_control=new, valid=r.valid, reason=r.reason, err=r.verdict.op_norm_error, wall=time.time() - t)
    print(row, flush=True); rows.append(row)
json.dump(dict(commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), seed=215, rows=rows), open("results/rishon/tester-215-mutants2.json", "w"), indent=1, default=float)
