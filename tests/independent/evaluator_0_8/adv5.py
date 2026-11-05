from common import *
from qiskit.quantum_info import Operator, random_unitary
from qiskit.circuit.library import UnitaryGate
from su2plaq.evaluate.evaluator import specialise, classify_outer_gates
from su2plaq.encodings.base import Layout
rng = np.random.default_rng(20261104)
n = 7; OUTQ = [4, 6]; INQ = [0, 1, 2, 3, 5]
lay = Layout(data=INQ, outer=OUTQ, ancilla=[])
def rand_circ(ng):
    qc = QuantumCircuit(n); used = set()
    for _ in range(ng):
        k = rng.integers(0, 24)
        a, b, c = rng.choice(INQ, 3, replace=False); o1, o2 = OUTQ if rng.random() < .5 else OUTQ[::-1]
        th = rng.uniform(-3, 3)
        if k == 0: qc.h(a)
        elif k == 1: qc.rx(th, a)
        elif k == 2: qc.cx(a, b)
        elif k == 3: qc.ccx(a, b, c)
        elif k == 4: qc.p(th, o1); used.add(o1)
        elif k == 5: qc.rz(th, o1); used.add(o1)
        elif k == 6: qc.cz(o1, a); used |= {o1}
        elif k == 7: qc.cp(th, o1, a); used |= {o1}
        elif k == 8: qc.cp(th, o1, o2); used |= {o1, o2}
        elif k == 9: qc.cx(o1, a); used |= {o1}
        elif k == 10: qc.ccx(o1, a, b); used |= {o1}
        elif k == 11: qc.ccx(o1, o2, a); used |= {o1, o2}
        elif k == 12: qc.cz(o1, o2); used |= {o1, o2}
        elif k == 13: qc.ccz(o1, o2, a); used |= {o1, o2}
        elif k == 14: qc.cry(th, o1, a); used |= {o1}
        elif k == 15: qc.append(UnitaryGate(np.block([[np.eye(2),np.zeros((2,2))],[np.zeros((2,2)),random_unitary(2, seed=int(rng.integers(1e9))).data]])), [a, o1]); used |= {o1}
        elif k == 16: qc.ch(o1, a); used |= {o1}
        elif k == 17: qc.t(o1); qc.sdg(o2); used |= {o1, o2}
        elif k == 18: qc.append(UnitaryGate(random_unitary(4, seed=int(rng.integers(1e9)))), [a, b])
        elif k == 19: qc.swap(a, b)
        elif k == 20: qc.crz(th, o1, a); used |= {o1}
        elif k == 21: qc.cswap(o1, a, b); used |= {o1}
        elif k == 22: qc.z(o1); qc.s(o1); used |= {o1}
        elif k == 23: qc.u(th, 0.3, -1.1, a)
    qc.global_phase = rng.uniform(-3, 3)
    return qc, used
def blk(U, read, pat):
    N = U.shape[0]; idx = np.arange(N); sel = np.ones(N, bool)
    for i, q in enumerate(sorted(read)): sel &= ((idx >> q) & 1) == ((pat >> i) & 1)
    return U[np.ix_(sel, sel)], sel
worst = 0; ncirc = 0; nbad_class = 0; patterns = 0
for t in range(60):
    qc, used = rand_circ(int(rng.integers(5, 25)))
    cls = classify_outer_gates(qc, lay)
    if cls != used: nbad_class += 1; print("classify mismatch", cls, used)
    U = Operator(qc).data
    for pat in range(2 ** len(used)):
        sc = specialise(qc, used, pat)
        Us = Operator(sc).data
        b1, sel = blk(U, used, pat); b2, _ = blk(Us, used, pat)
        worst = max(worst, np.abs(b1 - b2).max()); patterns += 1
        # specialised circuit must be idle on read qubits
        for inst in sc.data:
            if any(sc.find_bit(q).index in used for q in inst.qubits): raise SystemExit("read qubit still used")
    ncirc += 1
rec("specialise vs Operator blocks (random circuits)", "<=1e-12", f"{ncirc} circuits, {patterns} patterns, worst {worst:.2e}; classify mismatches {nbad_class}", 1e-12, worst < 1e-12 and nbad_class == 0)
# non-diagonal gate on outer inside random circuit => OuterWriteError
from su2plaq.evaluate.evaluator import OuterWriteError
qc = QuantumCircuit(n); qc.cx(0, 4)
try: classify_outer_gates(qc, lay); rec("classify: cx onto outer", "OuterWriteError", "none", "", False)
except OuterWriteError: rec("classify: cx onto outer", "OuterWriteError", "raised", "", True)
json.dump(RES, open(OUT+"adv5.json", "w"), indent=1)
