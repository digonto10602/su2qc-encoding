"""Tester 433: effect on the production metrics of deleting the two X-X mirror pairs that survive the mirror-pair battery (gates 70/339 on q7, 184/216 on q12)."""
import sys, os, json, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("c", os.path.join(here, "433-common.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
from qiskit import QuantumCircuit
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress.metrics import metrics
s = rishon_spec('step'); qc = C.build_circuit("r06-F3-006", s)
def without(drop):
    out = QuantumCircuit(qc.num_qubits, global_phase=qc.global_phase)
    for j, i in enumerate(qc.data):
        if j not in drop: out.append(i.operation, [qc.find_bit(q).index for q in i.qubits])
    return out
res = {}
for name, drop in [("baseline", set()), ("pair q7", {70, 339}), ("pair q12", {184, 216}), ("pair q3", {143, 266}), ("pair q11", {69, 340}), ("all four pairs", {70, 339, 184, 216, 143, 266, 69, 340})]:
    m = metrics(without(drop), s, measured=True)
    res[name] = {k: m[k] for k in ("cx", "t_eps", "depth_ct", "qubits", "depth")}
    print(name, [qc.data[j].operation.name + str([qc.find_bit(q).index for q in qc.data[j].qubits]) for j in sorted(drop)], res[name])
json.dump(res, open(os.path.join(here, "433-xpairs.json"), "w"), indent=1)
