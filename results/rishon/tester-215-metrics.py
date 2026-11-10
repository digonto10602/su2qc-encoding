"""Tester 215 probe (c): metrics of the general step PROGRAM (built through the Builder in a fresh process) vs own Qiskit level-0 count
(transpile optimization_level=0 into {cx, h, s, sdg, t, tdg, x, z, rz, p}) and Report 5 (10102 CX / 166 rot / 10218 T_fixed); plus
pygridsynth T(1e-6) recount.  Writes results/rishon/tester-215-metrics.json."""
import json, subprocess, math, sys, time
import numpy as np
from qiskit import transpile
import su2plaq.rishon.compress as RC
from su2plaq.rishon.compress import spec as S, baselines as BL
from su2plaq.compress.evaluate import load_program
from su2plaq.compress import metrics as M

spec = S.rishon_spec("step")
path = BL.general_program_path(spec)
mod = load_program(str(path))
qc = mod.build(spec).circuit()
qc_ref = BL.general_circuit(spec)
print("program circuit qubits", qc.num_qubits, "ops", dict(qc.count_ops()))
print("reference circuit ops", dict(qc_ref.count_ops()))
m = M.metrics(qc, spec, measured=False)
basis = ["cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz", "p"]
low = transpile(qc, basis_gates=basis, optimization_level=0)
ops = low.count_ops(); print("level-0 ops", dict(ops))
def odd_pi4(th):
    k = th / (math.pi / 4); return abs(k - round(k)) < 1e-9 and round(k) % 2 == 1
def is_clifford(th):
    k = th / (math.pi / 2); return abs(k - round(k)) < 1e-9
rot = [i for i in low.data if i.operation.name in ("rz", "p")]
n_rot = sum(1 for i in rot if not is_clifford(float(i.operation.params[0])) and not odd_pi4(float(i.operation.params[0])))
n_t_rot = sum(1 for i in rot if odd_pi4(float(i.operation.params[0])))
t_fixed = ops.get("t", 0) + ops.get("tdg", 0) + n_t_rot
res = dict(commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(),
           own=dict(cx=ops.get("cx", 0), t_fixed=t_fixed, n_rot=n_rot, depth=low.depth(), qubits=qc.num_qubits),
           evaluator=dict(cx=m["cx"], t_fixed=m["t_fixed"], n_rot=m["n_rot"], depth=m["depth"], qubits=m["qubits"], depth_ct=m.get("depth_ct")),
           report5=dict(cx=10102, n_rot=166, t_fixed=10218))
print(res)
# pygridsynth recount of T(1e-6): sum over rotations
from su2plaq.metrics.cliffordt import pygridsynth_tcount
tot = 0; t0 = time.time()
cache = {}
for i in rot:
    th = float(i.operation.params[0])
    if is_clifford(th) or odd_pi4(th): continue
    key = round(th, 12)
    if key not in cache: cache[key] = pygridsynth_tcount(th, 1e-6)
    tot += cache[key]
res["own"]["t_eps_1e-6"] = t_fixed + tot; res["own"]["distinct_angles"] = len(cache); res["own"]["synth_wall"] = time.time() - t0
mm = M.metrics(qc, spec, measured=True)
res["evaluator"]["t_eps"] = mm["t_eps"]; res["evaluator"]["t_measured"] = mm["t_measured"]
print(res)
res["match"] = dict(cx=res["own"]["cx"] == m["cx"] == 10102, t_fixed=t_fixed == m["t_fixed"] == 10218, n_rot=n_rot == m["n_rot"] == 166, qubits=qc.num_qubits == m["qubits"] == 58, t_eps=res["own"]["t_eps_1e-6"] == mm["t_eps"])
print(res["match"])
json.dump(res, open("results/rishon/tester-215-metrics.json", "w"), indent=1, default=float)
