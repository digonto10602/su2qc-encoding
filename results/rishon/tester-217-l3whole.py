"""Tester 217: is the whole-circuit Qiskit L3 transpile of the general step circuit beyond the exact sparse engine (>1e6 amplitudes per input)?
Own sparse engine, ~80 input codes (40 seeded random + 40 of the 10-ancilla class), stop when the state exceeds 2e7 entries."""
import sys, importlib.util, time, json
import numpy as np
spec_ = importlib.util.spec_from_file_location('eng', 'results/rishon/tester-217-engine.py'); eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress import baselines as BL
s = rishon_spec('step')
t0 = time.time()
qc = BL.qiskit_l3_whole(s)
print('transpile', time.time() - t0, qc.count_ops().get('cx'), flush=True)
ops = eng.lower(qc); qs = eng.used_qubits(ops)
print('gates', len(ops), 'qubits', len(qs), flush=True)
T = eng.algebra_targets(s.alpha, s.beta)
rng = np.random.default_rng(217)
res = []
for c in np.unique(np.r_[rng.choice(1296, 40, replace=False), np.flatnonzero(np.load('results/rishon/tester-217-conc.npy')==10)[:40]]):
    sim = eng.Sim(T['codes'][[c]], qs)
    peak = 0; stop = None
    for gi, op in enumerate(ops):
        if op[0] == 'phase': continue
        sim.apply(*op[:3]); peak = max(peak, len(sim.key))
        if peak > 2e7: stop = gi; break
    res.append(dict(code_index=int(c), peak_entries=int(peak), stopped_at_gate=stop, n_gates=len(ops)))
    print(res[-1], flush=True)
    if len(res) % 10 == 0: json.dump(res, open('results/rishon/tester-217-l3whole.json', 'w'), indent=1)
json.dump(res, open('results/rishon/tester-217-l3whole.json', 'w'), indent=1)
