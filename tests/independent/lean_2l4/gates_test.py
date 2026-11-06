import json, random, subprocess, sys, itertools
import numpy as np
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from su2plaq.lean import exact as E, certify as C
random.seed(7); rng = np.random.default_rng(7)
ARITY = dict(x=1,z=1,s=1,sdg=1,t=1,tdg=1,h=1,sx=1,rz=1,p=1,cx=2,cz=2,cp=2,swap=2,ccx=3,ccz=3)
N = 5
def run(gates, tag):
    cert = {"schema":"su2plaq-cert-1","n_qubits":N,"n_data":0,"n_outer":0,"base":{"d_alpha":1,"d_beta":1},"gates":gates}
    p = f"gt-{tag}.json"; json.dump(cert, open(p,"w"))
    U = np.zeros((2**N,2**N),complex)
    return p
def evalmat(gates, th, tag):
    p = run(gates, tag)
    U = np.zeros((2**N,2**N),complex)
    for col in range(2**N):
        for key, lp in C.checker_eval(p, col):
            U[key, col] += lp.evaluate(*th)
    return U
def qc_of(gates, th):
    qc = QuantumCircuit(N)
    for g in gates:
        name, q = g["g"], g["q"]
        m = g.get("m", [0,0]); ang = m[0]*th[0] + m[1]*th[1]
        if name in ("rz","p"): getattr(qc,name)(ang, *q)
        elif name == "cp": qc.cp(ang, *q)
        else: getattr(qc,name)(*q)
    return qc
def rand_gate(name):
    qs = random.sample(range(N), ARITY[name]); g = {"g":name,"q":qs}
    if name in ("rz","p","cp"):
        ma, mb = random.randint(-7,7), random.randint(-7,7)
        if name == "rz": ma, mb = 2*ma, 2*mb
        g["m"] = [ma, mb]
    return g
worst = 0
# every gate alone on random qubits, many random angles
for name in ARITY:
    w = 0
    for trial in range(6):
        g = rand_gate(name); th = tuple(rng.uniform(-3, 3, 2))
        U = evalmat([g], th, "one")
        ref = Operator(qc_of([g], th)).data
        w = max(w, np.abs(U-ref).max())
    print(f"gate {name:5s} exact vs qiskit (no phase freedom) max|diff| = {w:.2e}")
    worst = max(worst, w)
# random 40-gate circuits
names = list(ARITY)
for t in range(10):
    gates = [rand_gate(random.choice(names)) for _ in range(40)]
    th = tuple(rng.uniform(-3, 3, 2))
    U = evalmat(gates, th, "rand")
    ref = Operator(qc_of(gates, th)).data
    d = np.abs(U-ref).max(); worst = max(worst, d)
    print(f"random 40-gate circuit {t}: max|diff| = {d:.2e}; unitarity {np.abs(U.conj().T@U-np.eye(2**N)).max():.1e}")
print("WORST", worst)
