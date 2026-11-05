"""N6: subclasses of Qiskit standard-gate classes with overridden _define/to_matrix.  Truth = the INTENDED content (hand-built circuit).
Usage: PYTHONPATH=src python tests/independent/audit_fixes/subclass_spoof.py results/m1_audit_fixes_subclass_spoof.json"""
import sys, json, warnings
import numpy as np
warnings.filterwarnings("ignore")
import qiskit.circuit.library as L
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
import su2plaq.evaluate.sparse_sim as ss
from su2plaq.metrics.logical import lower

def dense_of(b, ncol):
    d = np.zeros((2 ** b.n_qubits, ncol), complex); np.add.at(d, (b.keys, b.cols), b.amps); return d
def circ(gate, qs, n=3):
    qc = QuantumCircuit(n); qc.h(range(n)); qc.append(gate, qs); qc.t(n - 1); return qc
def intended(fn, n=3):
    qc = QuantumCircuit(n); qc.h(range(n)); fn(qc); qc.t(n - 1); return qc

def mk(base, defn, mat, clsname=None, module=None):
    ns = {"_define": defn, "to_matrix": mat}
    if module: ns["__module__"] = module
    return type(clsname or base.__name__, (base,), ns)

def d_rx(self): q = QuantumCircuit(1); q.rx(self.params[0], 0); self.definition = q
def d_h(self): q = QuantumCircuit(1); q.h(0); self.definition = q
def d_x(self): q = QuantumCircuit(1); q.x(0); self.definition = q
def d_cz(self): q = QuantumCircuit(2); q.cz(0, 1); self.definition = q
def d_ccz(self): q = QuantumCircuit(3); q.ccz(0, 1, 2); self.definition = q
m_rx = lambda self, *a, **k: L.RXGate(self.params[0]).to_matrix()
m_h = lambda self, *a, **k: L.HGate().to_matrix()
m_x = lambda self, *a, **k: L.XGate().to_matrix()
m_cz = lambda self, *a, **k: L.CZGate().to_matrix()
m_ccz = lambda self, *a, **k: L.CCZGate().to_matrix()

cases = []   # (label, gate, qubits, intended-fn)
cases.append(("RZGate-named subclass (other module), content RX", mk(L.RZGate, d_rx, m_rx, "RZGate", "userpkg")(0.7), [0], lambda q: q.rx(0.7, 0)))
cases.append(("MyRZ subclass (other name), content RX", mk(L.RZGate, d_rx, m_rx, "MyRZ")(0.7), [0], lambda q: q.rx(0.7, 0)))
cases.append(("XGate-named subclass, content H", mk(L.XGate, d_h, m_h, "XGate", "userpkg")(), [0], lambda q: q.h(0)))
cases.append(("TGate-named subclass, content X", mk(L.TGate, d_x, m_x, "TGate", "userpkg")(), [0], lambda q: q.x(0)))
cases.append(("TGate-named subclass, module forged qiskit.*", mk(L.TGate, d_x, m_x, "TGate", "qiskit.circuit.library.standard_gates.t")(), [0], lambda q: q.x(0)))
cases.append(("HGate-named subclass, content X", mk(L.HGate, d_x, m_x, "HGate", "userpkg")(), [0], lambda q: q.x(0)))
cases.append(("CXGate-named subclass, content CZ", mk(L.CXGate, d_cz, m_cz, "CXGate", "userpkg")(), [0, 1], lambda q: q.cz(0, 1)))
cases.append(("CCXGate-named subclass, content CCZ", mk(L.CCXGate, d_ccz, m_ccz, "CCXGate", "userpkg")(), [0, 1, 2], lambda q: q.ccz(0, 1, 2)))
cases.append(("MyT (other name, singleton base), content X", mk(L.TGate, d_x, m_x, "MyT")(), [0], lambda q: q.x(0)))
cases.append(("MyH (other name), content X", mk(L.HGate, d_x, m_x, "MyH")(), [0], lambda q: q.x(0)))
# subclass overriding ONLY _define (definition) -- to_matrix inherited from the standard class
def only_def(base, defn, nm, mod=None):
    ns = {"_define": defn}
    if mod: ns["__module__"] = mod
    return type(nm, (base,), ns)
cases.append(("TGate-named subclass, ONLY _define overridden (X)", only_def(L.TGate, d_x, "TGate", "userpkg")(), [0], lambda q: q.x(0)))
cases.append(("RZGate-named subclass, ONLY _define overridden (RX)", only_def(L.RZGate, d_rx, "RZGate", "userpkg")(0.7), [0], lambda q: q.rx(0.7, 0)))
rows = []
for label, g, qs, fn in cases:
    n = 3
    qc = circ(g, qs, n); ref = intended(fn, n)
    Ur = Operator(ref).data
    r = dict(case=label, cls=f"{type(g).__module__}.{type(g).__qualname__}", is_standard_gate=ss.is_standard_gate(g), name=g.name)
    try:
        b = ss.run_batch(qc, np.arange(2 ** n, dtype=np.int64)); r["sim_err_vs_intended"] = float(np.abs(dense_of(b, 2 ** n) - Ur).max())
        r["sim"] = "ok" if r["sim_err_vs_intended"] < 1e-10 else "WRONG (silently trusted)"
    except ValueError as e:
        r["sim"] = "rejected"; r["sim_err_vs_intended"] = None
    try:
        Lc = lower(qc); Ul = Operator(Lc).data; ov = np.trace(Ur.conj().T @ Ul); r["lower_err_vs_intended"] = float(np.abs(Ul * (abs(ov) / ov) - Ur).max())
        lc = dict(Lc.count_ops()); rc = dict(lower(ref).count_ops()); r["lower_counts"] = lc; r["intended_counts"] = rc
        r["lower"] = "ok" if r["lower_err_vs_intended"] < 1e-10 and lc == rc else "WRONG (silently trusted)"
    except ValueError as e:
        r["lower"] = "rejected"
    rows.append(r); print(r["case"], "| std?", r["is_standard_gate"], "| sim:", r["sim"], "| lower:", r["lower"], flush=True)
json.dump(rows, open(sys.argv[1], "w"), indent=1, default=str)
