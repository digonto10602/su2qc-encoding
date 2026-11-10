import sys, json; sys.path.insert(0, "src")
from qiskit import QuantumCircuit, transpile
from su2plaq.circuits.spinnet import build_UB
B = ["cx","h","s","sdg","t","tdg","x","z","rz"]
ub = build_UB(0.61); out = {}
for name, qs in {"none": [], "q0-3": range(4), "data0-7": range(8), "all15": range(15), "ancillas8-14": range(8, 15), "corners4-7": range(4, 8)}.items():
    pre = QuantumCircuit(*ub.qregs)
    for q in qs: pre.p(0.1, q)
    pre.compose(ub, inplace=True)
    out[f"head:{name}"] = transpile(pre, basis_gates=B, optimization_level=0, qubits_initially_zero=False).depth()
    post = QuantumCircuit(*ub.qregs); post.compose(ub, inplace=True)
    for q in qs: post.p(0.1, q)
    out[f"tail:{name}"] = transpile(post, basis_gates=B, optimization_level=0, qubits_initially_zero=False).depth()
print(out); json.dump(out, open("results/spinnet/tester/m3_steps_3_3_3_5_depth_probe.json", "w"))
