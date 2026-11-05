from common import *
from qiskit.quantum_info import random_unitary
from qiskit.circuit.library import UnitaryGate
from su2plaq.evaluate.evaluator import classify_outer_gates, OuterWriteError
from su2plaq.encodings.base import Layout
n=7; lay = Layout(data=[0,1,2,3,5], outer=[4,6], ancilla=[])
cases = {
 "cry(o,a)": lambda q: q.cry(0.7,4,0), "crx": lambda q: q.crx(0.7,4,0), "crz": lambda q: q.crz(0.7,4,0), "ch": lambda q: q.ch(4,0),
 "cu": lambda q: q.cu(0.3,0.4,0.5,0.6,4,0), "cs": lambda q: q.cs(4,0), "csx": lambda q: q.csx(4,0), "cy": lambda q: q.cy(4,0),
 "cswap(o;a,b)": lambda q: q.cswap(4,0,1), "controlled UnitaryGate(2x2)": lambda q: q.append(UnitaryGate(random_unitary(2,seed=1)).control(1),[4,0]),
 "UnitaryGate 2q [o,a] diag-on-o by construction": lambda q: q.append(UnitaryGate(np.kron(np.diag([1,1j]), random_unitary(2,seed=2).data)),[4,0]),
 "c-unitary block-diag matrix, 2q (|0><0|⊗I+|1><1|⊗U)": lambda q: q.append(UnitaryGate(np.block([[np.eye(2),np.zeros((2,2))],[np.zeros((2,2)),random_unitary(2,seed=3).data]])),[0,4]),
 "mcrx 2 ctrl (o,a->b)": lambda q: q.append(__import__('qiskit.circuit.library',fromlist=['RXGate']).RXGate(0.5).control(2),[4,6,0]),
 "mcp 2": lambda q: q.mcp(0.4,[4,6],0), "rzz(o,a)": lambda q: q.rzz(0.5,4,0), "rzz(a,o)": lambda q: q.rzz(0.5,0,4),
 "rxx(o,a)": lambda q: q.rxx(0.5,4,0), "ccx(a,b,o)": lambda q: q.ccx(0,1,4),
}
for name, f in cases.items():
    qc = QuantumCircuit(n); f(qc)
    try: r = classify_outer_gates(qc, lay); print(f"{name:55s} read={sorted(r)}")
    except OuterWriteError as e: print(f"{name:55s} REJECT {e}")
