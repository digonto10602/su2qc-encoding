import sys, json, pathlib, time, os
sys.path.insert(0, "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv")
from cases import prog, UE_CORE, SP
(SP/"programs").mkdir(exist_ok=True)
imports = '''import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Gate
from qiskit.circuit.library import HGate, XGate, UnitaryGate, CXGate, CZGate, CCXGate, RZGate, SGate
'''
def tamper(code):
    return prog(f'''{imports}
def build(spec):
{UE_CORE}    qc = b.circuit()
{code}
    b.circuit = lambda: qc
    return b
''')
X = {}
X["x_mut_H_named_z_pair"] = tamper('''    g = HGate().to_mutable(); g.name = "z"
    qc.append(g, [0]); qc.append(g.copy(), [0])''')
X["x_CX_named_cz_with_CZ"] = tamper('''    g = CXGate().to_mutable(); g.name = "cz"
    qc.append(g, [0,1]); qc.append(CZGate(), [0,1])''')
X["x_CZ_named_cx_with_CZ"] = tamper('''    g = CZGate().to_mutable(); g.name = "cx"
    qc.append(g, [0,1]); qc.append(CZGate(), [0,1])''')
X["x_custom_identity_named_h"] = tamper('''    inner = QuantumCircuit(1)
    g = Gate("h", 1, []); g.definition = inner
    qc.append(g, [0])''')
X["x_custom_identity_named_z_two"] = tamper('''    inner = QuantumCircuit(1)
    g = Gate("z", 1, []); g.definition = inner
    qc.append(g, [0]); qc.append(g, [0])''')
X["x_unitary_named_x_pair"] = tamper('''    u = UnitaryGate(np.eye(2)); u.name = "x"
    qc.append(u, [0])''')
X["x_hidden_Tgates_in_cx_named_custom"] = tamper('''    inner = QuantumCircuit(2); inner.t(0); inner.tdg(0); inner.cx(0,1); inner.cx(0,1)
    g = inner.to_gate(); g.name = "cx"
    qc.append(g, [0,1])''')
X["x_clbit_measure"] = tamper('''    from qiskit.circuit import ClassicalRegister
    qc.add_register(ClassicalRegister(1)); qc.measure(0, 0)''')
X["x_global_phase_free"] = tamper('''    qc.global_phase += 1.2345''')
X["x_barrier_label"] = tamper('''    qc.barrier(); qc.id(0)''')
X["x_30_hadamard_ancillas"] = prog(f'''def build(spec):
{UE_CORE}    a = b.alloc(30)
    for q in a: b.h(q)
    for q in a: b.h(q)
    return b
''')
X["x_5_hadamard_ancillas_clean"] = prog(f'''def build(spec):
{UE_CORE}    a = b.alloc(5)
    for q in a: b.h(q)
    for q in a: b.h(q)
    return b
''')
X["x_circuit_with_huge_gate_count"] = prog(f'''def build(spec):
{UE_CORE}    for _ in range(60000):
        b.x(d[0]); b.x(d[0])
    return b
''')
for k, v in X.items(): (SP/"programs"/f"{k}.py").write_text(v)
print(list(X))
