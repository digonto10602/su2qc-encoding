"""Tester: mirror() with rc3x / rc3x_dg / rccx: compute + mirror(compute) must be identity (ancillas back to 0, no phase), and
classical_slots (Toffoli semantics) must match |amplitude|^2 support of the actual RC3X action on basis states. Deterministic."""
import sys, json, numpy as np
sys.path.insert(0, "src")
from qiskit import QuantumCircuit
from qiskit.circuit.library import RC3XGate
from qiskit.quantum_info import Operator, Statevector
from su2plaq.spinnet.walk import mirror
compute = [("x", 2), ("rc3x", 0, 1, 2, 4), ("rccx", 3, 4, 5), ("rc3x_dg", 1, 4, 5, 6), ("x", 0)]
def add(qc, st):
    for s in st:
        if s[0] == "x": qc.x(s[1])
        elif s[0] == "rccx": qc.rccx(*s[1:])
        elif s[0] == "rc3x": qc.append(RC3XGate(), list(s[1:]))
        elif s[0] == "rc3x_dg": qc.append(RC3XGate().inverse(), list(s[1:]))
qc = QuantumCircuit(7); add(qc, compute); add(qc, mirror(compute))
U = Operator(qc).data
res = {"compute_then_mirror_minus_identity": float(np.abs(U - np.eye(128)).max())}
# classical action: the RC3X acting on basis states of 4 qubits -> support
g = Operator(RC3XGate()).data   # qubits (c0,c1,c2,t) little-endian
bad = 0
for x in range(16):
    v = g[:, x]; out = int(np.argmax(np.abs(v)))
    exp = x ^ (8 if (x & 7) == 7 else 0)
    bad += (out != exp) or abs(abs(v[out]) - 1) > 1e-12
res["rc3x_classical_mismatch"] = int(bad)
# is the plain RC3X self-inverse (plan says no)?
res["rc3x_squared_minus_identity"] = float(np.abs(g @ g - np.eye(16)).max())
print(json.dumps(res)); json.dump(res, open(sys.argv[1], "w"))
