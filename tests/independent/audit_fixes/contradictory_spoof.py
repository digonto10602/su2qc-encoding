"""Gates whose to_matrix() contradicts their definition: what do sim / lower / Qiskit's transpiler follow?
Usage: PYTHONPATH=src python tests/independent/audit_fixes/contradictory_spoof.py out.json"""
import sys, json, warnings
import numpy as np
warnings.filterwarnings("ignore")
import qiskit.circuit.library as L
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
import su2plaq.evaluate.sparse_sim as ss
from su2plaq.metrics.logical import lower

def dense_of(b, ncol):
    d = np.zeros((2 ** b.n_qubits, ncol), complex); np.add.at(d, (b.keys, b.cols), b.amps); return d
def d_x(self): q = QuantumCircuit(1); q.x(0); self.definition = q
def d_rx(self): q = QuantumCircuit(1); q.rx(self.params[0], 0); self.definition = q
T_MAT = lambda self, *a, **k: L.TGate().to_matrix()
RZ_MAT = lambda self, *a, **k: L.RZGate(self.params[0]).to_matrix()
cases = [("TGate-named singleton subclass: definition X, to_matrix T", type("TGate", (L.TGate,), {"_define": d_x, "to_matrix": T_MAT, "__module__": "userpkg"})(), "x"),
         ("MyT: definition X, to_matrix T", type("MyT", (L.TGate,), {"_define": d_x, "to_matrix": T_MAT})(), "x"),
         ("RZGate-named subclass: definition RX, to_matrix RZ", type("RZGate", (L.RZGate,), {"_define": d_rx, "to_matrix": RZ_MAT, "__module__": "userpkg"})(0.7), "rx"),
         ("MyRZ: definition RX, to_matrix RZ", type("MyRZ", (L.RZGate,), {"_define": d_rx, "to_matrix": RZ_MAT})(0.7), "rx")]
rows = []
for label, g, kind in cases:
    n = 3; nq = 1
    qc = QuantumCircuit(n); qc.h(range(n)); qc.append(g, [0]); qc.t(2)
    D = QuantumCircuit(n); D.h(range(n)); D.x(0) if kind == "x" else D.rx(0.7, 0); D.t(2)           # definition semantics
    M = QuantumCircuit(n); M.h(range(n)); M.t(0) if kind == "x" else M.rz(0.7, 0); M.t(2)           # to_matrix semantics
    UD, UM = Operator(D).data, Operator(M).data
    b = ss.run_batch(qc, np.arange(8)); S = dense_of(b, 8)
    Lc = lower(qc); UL = Operator(Lc).data
    ph = lambda A, B: float(np.abs(A * (np.trace(B.conj().T @ A) / abs(np.trace(B.conj().T @ A))).conjugate() - B).max())
    tq = transpile(qc, basis_gates=["cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz"], optimization_level=0)
    r = dict(case=label, sim_vs_definition=float(np.abs(S - UD).max()), sim_vs_to_matrix=float(np.abs(S - UM).max()),
             lower_vs_definition=ph(UL, UD), lower_vs_to_matrix=ph(UL, UM),
             qiskit_transpile_vs_definition=ph(Operator(tq).data, UD), qiskit_transpile_vs_to_matrix=ph(Operator(tq).data, UM),
             qiskit_Operator_vs_definition=float(np.abs(Operator(qc).data - UD).max()), qiskit_Operator_vs_to_matrix=float(np.abs(Operator(qc).data - UM).max()),
             lower_counts=dict(Lc.count_ops()), is_standard_gate=ss.is_standard_gate(g))
    rows.append(r); print(json.dumps(r, default=str), flush=True)
json.dump(rows, open(sys.argv[1], "w"), indent=1)
