"""N6 residual: user subclasses of NON-singleton standard classes that reuse Qiskit's class name (RZGate, PhaseGate, CPhaseGate, UGate, RXGate, CRXGate...).
Truth = intended content.  Usage: PYTHONPATH=src python tests/independent/audit_fixes/spoof_nonsingleton.py results/m1_audit_fixes_spoof_nonsingleton.json"""
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

def spoof(base, name, define_fn, mat_fn=None, module=None):
    ns = {"_define": define_fn}
    if mat_fn: ns["to_matrix"] = mat_fn
    if module: ns["__module__"] = module
    return type(name, (base,), ns)

def d(fn, nq):
    def _define(self):
        q = QuantumCircuit(nq); fn(q, self.params); self.definition = q
    return _define

cases = []
# (label, class name, base, args, nq, defn on q with params, intended-fn)
cases.append(("RZGate -> content RX", "RZGate", L.RZGate, (0.7,), 1, lambda q, p: q.rx(p[0], 0), lambda q: q.rx(0.7, 0)))
cases.append(("PhaseGate -> content RZ", "PhaseGate", L.PhaseGate, (0.7,), 1, lambda q, p: q.rz(p[0], 0), lambda q: q.rz(0.7, 0)))
cases.append(("CPhaseGate -> content CRZ", "CPhaseGate", L.CPhaseGate, (0.7,), 2, lambda q, p: q.crz(p[0], 0, 1), lambda q: q.crz(0.7, 0, 1)))
cases.append(("UGate -> content RX", "UGate", L.UGate, (0.7, 0.1, 0.2), 1, lambda q, p: q.rx(p[0], 0), lambda q: q.rx(0.7, 0)))
cases.append(("RXGate -> content RY", "RXGate", L.RXGate, (0.7,), 1, lambda q, p: q.ry(p[0], 0), lambda q: q.ry(0.7, 0)))
cases.append(("CRXGate -> content CRY", "CRXGate", L.CRXGate, (0.7,), 2, lambda q, p: q.cry(p[0], 0, 1), lambda q: q.cry(0.7, 0, 1)))
cases.append(("SXGate (singleton) -> content X", "SXGate", L.SXGate, (), 1, lambda q, p: q.x(0), lambda q: q.x(0)))
rows = []
for label, nm, base, args, nq, fn, intended in cases:
    for with_to_matrix in (False, True):
        cls = spoof(base, nm, d(fn, nq), (lambda self, *a, **k: Operator(self.definition).data) if with_to_matrix else None, "userpkg.gates")
        g = cls(*args)
        n = 3
        qc = QuantumCircuit(n); qc.h(range(n)); qc.append(g, list(range(nq))); qc.t(n - 1)
        ref = QuantumCircuit(n); ref.h(range(n)); intended(ref); ref.t(n - 1)
        Ur = Operator(ref).data
        r = dict(case=label, to_matrix_overridden=with_to_matrix, cls=f"{type(g).__module__}.{type(g).__qualname__}", is_standard_gate=ss.is_standard_gate(g))
        try:
            b = ss.run_batch(qc, np.arange(2 ** n)); r["sim_err"] = float(np.abs(dense_of(b, 2 ** n) - Ur).max()); r["sim"] = "ok" if r["sim_err"] < 1e-10 else "WRONG (trusted by name)"
        except ValueError as e:
            r["sim"] = "rejected"
        try:
            Lc = lower(qc); Ul = Operator(Lc).data; ov = np.trace(Ur.conj().T @ Ul); e = float(np.abs(Ul * (abs(ov) / ov) - Ur).max()); r["lower_err"] = e
            r["lower"] = "ok" if e < 1e-10 else "WRONG (trusted by name)"
        except ValueError as e:
            r["lower"] = "rejected"
        rows.append(r); print(r["case"], "to_matrix_override" if with_to_matrix else "define-only", "| std?", r["is_standard_gate"], "| sim:", r["sim"], "| lower:", r["lower"], flush=True)
json.dump(rows, open(sys.argv[1], "w"), indent=1, default=str)
