"""Validate my gate simulator vs Qiskit Operator on random small circuits."""
import sys, json; sys.path.insert(0, 'results/rishon')
import importlib.util
spec = importlib.util.spec_from_file_location('mysim', 'results/rishon/tester-204-mysim.py'); ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
rng = np.random.default_rng(204)
worst = 0
for trial in range(40):
    nq = 5
    qc = QuantumCircuit(nq)
    for _ in range(25):
        g = rng.choice(['x','z','h','cx','cz','ch','ccx','ccz','crx','p'])
        a = rng.permutation(nq)
        if g in 'xzh' and len(g)==1 or g=='h': qc.__getattribute__(g)(int(a[0]))
        elif g == 'p': qc.p(float(rng.uniform(-3,3)), int(a[0]))
        elif g in ('cx','cz','ch'): getattr(qc, g)(int(a[0]), int(a[1]))
        elif g in ('ccx','ccz'): getattr(qc, g)(int(a[0]), int(a[1]), int(a[2]))
        elif g == 'crx': qc.crx(float(rng.uniform(-3,3)), int(a[0]), int(a[1]))
    Uq = Operator(qc).data
    ms.NQ_SHIFT = nq
    # my sim expects data/ancilla layout: just use own class with nq and 2**nq inputs
    sim = ms.Sim(np.arange(2**nq), nq)
    sim.run(qc)
    M = np.zeros((2**nq, 2**nq), complex)
    st = sim.key & ((1<<nq)-1); col = sim.key >> nq
    np.add.at(M, (st, col), sim.amp)
    worst = max(worst, np.abs(M - Uq).max())
print('max |mysim - Qiskit Operator| over 40 random 5-qubit circuits:', worst)
json.dump({'max_diff': float(worst), 'trials': 40, 'seed': 204}, open('results/rishon/tester-204-simcheck.json','w'))
