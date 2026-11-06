import sys, json, random
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from su2plaq.lean import certify as C
random.seed(3); rng = np.random.default_rng(3)
a, b = 0.37, 0.61
N = 4
worst = 0
def check(qc, tag):
    global worst
    # exporter lowering
    ops, gph = C._translate_export(qc)
    names = {o[0] for o in ops}
    assert not ({"u", "unitary"} & names), names
    p = C.export_raw_circuit(qc, f"low-{tag}.json", alpha=a, beta=b)
    assert not isinstance(p, str), p
    base = json.load(open(p))["base"]
    th = (a / base["d_alpha"], b / base["d_beta"])
    U = np.zeros((2**N, 2**N), complex)
    for col in range(2**N):
        for key, lp in C.checker_eval(p, col): U[key, col] += lp.evaluate(*th)
    ref = Operator(qc).data
    d = np.abs(U - ref).max()      # exact global phase (qc.global_phase included in Operator; our circuits have 0)
    worst = max(worst, d); return d
# angles that are rational multiples of alpha/beta so the exporter can recognise them
res = []
for g in ("crx", "crz", "rx"):
    for trial in range(4):
        qc = QuantumCircuit(N)
        r = random.choice([1, -1, 2, -3, 4]) * random.choice([1, 2, 4])
        ang = r * random.choice([a, b]) / random.choice([1, 2, 4])
        qs = random.sample(range(N), 2 if g != "rx" else 1)
        qc.h(0)   # something around
        getattr(qc, g)(ang, *qs)
        d = check(qc, f"{g}{trial}"); res.append((g, ang, d))
        print(f"{g}({ang:+.5f}) on {qs}: max|exact lowering - Qiskit Operator| = {d:.2e}")
# crx at negative control order, chain mix
qc = QuantumCircuit(N); qc.crx(-4*b, 3, 0); qc.crx(a/2, 0, 3); qc.rx(2*b, 1); qc.crz(-b, 2, 1); qc.cx(1, 2)
print("mix:", check(qc, "mix"))
print("WORST", worst)
