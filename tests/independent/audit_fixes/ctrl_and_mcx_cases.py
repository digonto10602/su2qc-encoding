"""Open-control / annotated gates (genuine standard gates must be simulated and lowered exactly) and mcx>=3 hidden inside gates
with standard names (must be rejected).  Usage: PYTHONPATH=src python tests/independent/audit_fixes/ctrl_and_mcx_cases.py out.json"""
import sys, json, warnings
import numpy as np
warnings.filterwarnings("ignore")
from qiskit import QuantumCircuit
from qiskit.circuit.library import RZGate, HGate, PhaseGate, XGate, SwapGate, ZGate
from qiskit.quantum_info import Operator
import su2plaq.evaluate.sparse_sim as ss
from su2plaq.metrics.logical import lower

def dense_of(b, ncol):
    d = np.zeros((2 ** b.n_qubits, ncol), complex); np.add.at(d, (b.keys, b.cols), b.amps); return d
rows = []
def run(label, qc, expect):
    n = qc.num_qubits
    try:
        b = ss.run_batch(qc, np.arange(2 ** n)); s = "ok" if np.abs(dense_of(b, 2 ** n) - Operator(qc).data).max() < 1e-12 else "WRONG"
        se = float(np.abs(dense_of(b, 2 ** n) - Operator(qc).data).max())
    except ValueError as e:
        s, se = "rejected", None
    try:
        L = lower(qc); Ul = Operator(L).data; Uo = Operator(qc).data; ov = np.trace(Uo.conj().T @ Ul)
        le = float(np.abs(Ul * (abs(ov) / ov) - Uo).max()); l = "ok" if le < 1e-12 else "WRONG"
    except ValueError as e:
        l, le = "rejected", None
    good = (s == "ok" and l == "ok") if expect == "exact" else (s == "rejected" and l == "rejected")
    rows.append(dict(case=label, expect=expect, sim=s, sim_err=se, lower=l, lower_err=le, good=good))
    print(("PASS" if good else "FAIL"), label, "| sim", s, se, "| lower", l, le, flush=True)

gens = {
 "cx cs=0": lambda q: q.cx(0, 2, ctrl_state=0), "cx cs=1": lambda q: q.cx(0, 2, ctrl_state=1),
 "ccx cs=0/1/2": lambda q: (q.ccx(0, 1, 2, ctrl_state=0), q.ccx(0, 1, 2, ctrl_state=1), q.ccx(0, 1, 2, ctrl_state=2)),
 "ch cs=0": lambda q: q.ch(0, 2, ctrl_state=0), "cz cs=0": lambda q: q.cz(0, 2, ctrl_state=0), "ccz cs=1": lambda q: q.ccz(0, 1, 2, ctrl_state=1),
 "crx cs=0": lambda q: q.crx(.3, 0, 2, ctrl_state=0), "cry cs=0": lambda q: q.cry(.3, 0, 2, ctrl_state=0), "crz cs=0": lambda q: q.crz(.3, 0, 2, ctrl_state=0),
 "cp cs=0": lambda q: q.cp(.3, 0, 2, ctrl_state=0), "cswap cs=0": lambda q: q.cswap(0, 1, 2, ctrl_state=0),
 "X.control(1,cs=0)": lambda q: q.append(XGate().control(1, ctrl_state=0), [0, 1]),
 "X.control(1,annotated)": lambda q: q.append(XGate().control(1, annotated=True), [0, 1]),
 "X.control(1,annotated,cs=0)": lambda q: q.append(XGate().control(1, ctrl_state=0, annotated=True), [0, 1]),
 "Z.control(1,annotated)": lambda q: q.append(ZGate().control(1, annotated=True), [0, 1]),
 "H.control(1,annotated)": lambda q: q.append(HGate().control(1, annotated=True), [0, 1]),
 "X.control(2,cs=0)": lambda q: q.append(XGate().control(2, ctrl_state=0), [0, 1, 2]),
 "H.control(2,cs=1)": lambda q: q.append(HGate().control(2, ctrl_state=1), [0, 1, 2]),
 "RZ.control(1,cs=0)": lambda q: q.append(RZGate(.4).control(1, ctrl_state=0), [0, 2]),
 "RZ.control(2,cs=3)": lambda q: q.append(RZGate(.4).control(2, ctrl_state=3), [0, 1, 2]),
 "Swap.control(1,cs=0)": lambda q: q.append(SwapGate().control(1, ctrl_state=0), [0, 1, 2]),
}
for k, f in gens.items():
    q = QuantumCircuit(3); q.h(range(3)); f(q); q.t(2); run(k, q, "exact")
q = QuantumCircuit(4); q.h(range(4)); q.append(RZGate(.4).control(3, ctrl_state=7), [0, 1, 2, 3]); run("RZ.control(3)", q, "exact")
# annotated cases that carry no definition we can use are allowed to be rejected: record separately
q = QuantumCircuit(4); q.h(range(4)); q.append(RZGate(.4).control(2, annotated=True), [0, 1, 2]); n = 4
try:
    b = ss.run_batch(q, np.arange(2 ** n)); e = float(np.abs(dense_of(b, 2 ** n) - Operator(q).data).max()); rows.append(dict(case="RZ.control(2,annotated)", sim="ok" if e < 1e-12 else "WRONG", sim_err=e, good=e < 1e-12)); print("RZ.control(2,annotated) sim", e)
except ValueError as ex:
    rows.append(dict(case="RZ.control(2,annotated)", sim="rejected", good=True)); print("RZ.control(2,annotated) rejected (allowed)")
# mcx>=3 inside gates with standard names: must be rejected
for nm in ("my_wrap", "cx", "h", "t", "x", "ccx", "barrier", "rz", "unitary", "ccz", "swap"):
    for ctrl in (3, 4):
        inner = QuantumCircuit(ctrl + 1, name=nm); inner.mcx(list(range(ctrl)), ctrl)
        qc = QuantumCircuit(ctrl + 3); qc.h(range(ctrl + 3)); qc.append(inner.to_gate(), range(ctrl + 1))
        run(f"mcx{ctrl} inside gate named {nm}", qc, "rejected")
# nested two deep, with standard names at both levels
a = QuantumCircuit(4, name="cx"); a.mcx([0, 1, 2], 3); b_ = QuantumCircuit(4, name="h"); b_.append(a.to_gate(), range(4))
qc = QuantumCircuit(6); qc.h(range(6)); qc.append(b_.to_gate(), range(4)); run("mcx3 nested cx>h", qc, "rejected")
# mcx2 (= ccx) and rccx are allowed
qc = QuantumCircuit(4); qc.h(range(4)); qc.mcx([0, 1], 2); run("mcx2", qc, "exact")
print("n", len(rows), "bad", sum(not r["good"] for r in rows))
json.dump(rows, open(sys.argv[1], "w"), indent=1)
