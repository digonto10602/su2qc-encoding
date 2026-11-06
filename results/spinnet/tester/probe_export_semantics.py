"""Tester 3.L3: the exported gate list (what the Lean checker replays) vs the Qiskit circuit it was exported from, on
sampled basis states and random physical superpositions (23 qubits, Statevector).  Angles m = (ma, mb): theta = ma*alpha/dA + mb*beta/dB."""
import json, sys, pathlib
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from su2plaq.circuits.spinnet import build_step
from su2plaq.encodings.spinnet import SpinNet
enc = SpinNet(); codes = [int(c[0]) for c in enc.physical_vectors().codes]
A, B = 0.37, 0.61
rng = np.random.default_rng(20261106)
out = {}
for order, path in ((1, 'results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json'), (2, sys.argv[1])):
    cert = json.loads(pathlib.Path(path).read_text())
    n = cert['n_qubits']; dA, dB = cert['base']['d_alpha'], cert['base']['d_beta']
    qc = build_step(A, B, order, with_outer=True)
    rec = QuantumCircuit(n)
    for g in cert['gates']:
        q = g['q']; nm = g['g']
        th = (g['m'][0] * A / dA + g['m'][1] * B / dB) if 'm' in g else None
        if nm == 'h': rec.h(q[0])
        elif nm == 'x': rec.x(q[0])
        elif nm == 'cx': rec.cx(*q)
        elif nm == 't': rec.t(q[0])
        elif nm == 'tdg': rec.tdg(q[0])
        elif nm == 'p': rec.p(th, q[0])
        elif nm == 'rz': rec.rz(th, q[0])
        else: raise SystemExit('unhandled ' + nm)
    ks = sorted(set(rng.integers(0, 433, 10).tolist() + [0, 432]))
    worst = 0.0; phases = []
    for k in ks:
        sv = Statevector.from_int(codes[k], 2 ** n)
        a = sv.evolve(qc); b = sv.evolve(rec)
        ov = np.vdot(a.data, b.data)
        worst = max(worst, abs(abs(ov) - 1)); phases.append(np.angle(ov))
    # random superposition of 5 physical states
    idx = rng.choice(433, 5, replace=False); amps = rng.normal(size=5) + 1j * rng.normal(size=5); amps /= np.linalg.norm(amps)
    v = np.zeros(2 ** n, complex)
    for i, a_ in zip(idx, amps): v[codes[i]] = a_
    sv = Statevector(v); a = sv.evolve(qc); b = sv.evolve(rec)
    ov = np.vdot(a.data, b.data); worst = max(worst, abs(abs(ov) - 1)); phases.append(np.angle(ov))
    out[order] = dict(states=ks, worst_1_minus_abs_overlap=worst, phase_overlap_min=min(phases), phase_overlap_max=max(phases), qc_global_phase=float(qc.global_phase))
    print(order, out[order])
json.dump(out, open(sys.argv[2], 'w'), indent=1)
