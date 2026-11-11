"""Tester 403 (b): recount CX / fixed T / rotations / T(eps) from saved QPY files; compare with results/lsh/*.json."""
import json, math, subprocess
import numpy as np
from qiskit import qpy
import pygridsynth as pg

def load(p):
    with open(p, "rb") as f: return qpy.load(f)[0]

def count(qc):
    cx = t = rot = 0; angs = []
    from qiskit import transpile
    # lower rccx/ccx to cx,h,t,tdg manually via qiskit decompose (definition), not via project code
    q = qc.decompose(gates_to_decompose=['rccx'])
    for i in q.data:
        n = i.operation.name
        if n == "cx": cx += 1
        elif n in ("t","tdg"): t += 1
        elif n in ("rz","p"):
            a = float(i.operation.params[0]); angs.append(a); rot += 1
    return cx, t, rot, angs, q.num_qubits, sorted({i.operation.name for i in q.data})

def tsyn(angs, eps):
    tot = 0
    for a in angs:
        s = pg.gridsynth_gates(theta=a, epsilon=eps)
        tot += str(s).count("T")
    return tot

out = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip(), "dirty": True, "rows": []}
for name in ["UE","UB","step","step_order2"]:
    qc = load(f"results/lsh/{name}.qpy")
    cx, t, rot, angs, nq, names = count(qc)
    row = dict(file=name, cx=cx, t_fixed=t, n_rot=rot, qubits=nq, gate_names=names)
    row["T_eps"] = {str(e): t + tsyn(angs, e) for e in (1e-4,1e-6,1e-8,1e-10)}
    # rotation-only check
    out["rows"].append(row); print(row, flush=True)
# outer row
qc = load("results/lsh/UE_outer_row.qpy"); cx,t,rot,angs,nq,names = count(qc)
out["rows"].append(dict(file="UE_outer_row", cx=cx, t_fixed=t, n_rot=rot, qubits=nq, T_eps={str(e): t+tsyn(angs,e) for e in (1e-4,1e-6,1e-8,1e-10)})); print(out["rows"][-1])
json.dump(out, open("results/lsh_tester/tester-403-recount.json","w"), indent=1)
