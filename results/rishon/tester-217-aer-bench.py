import sys, time, importlib.util, os
import numpy as np
sys.path.insert(0,'results/rishon')
spec_ = importlib.util.spec_from_file_location('aer', 'results/rishon/tester-217-aer.py'); aer = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(aer)
eng = aer.eng
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE
s = rishon_spec('step')
T = eng.algebra_targets(0.37, 0.61)
mod = LE.load_program('compress/programs/rishon/seed/000-general.py')
qc = mod.build(s).circuit()
ops = eng.lower(qc); qs = eng.used_qubits(ops)
anc, ever = aer.live_sets(qc, T, ops, qs)
nl = ever.sum(1)
for k in (2, 4, 5, 7, 8, 10):
    c = int(np.flatnonzero(nl == k)[0])
    live = [anc[j] for j in range(len(anc)) if ever[c, j]]
    code, sv, nq, dt, ng = aer.run_code((qc, int(T['codes'][c]), live, 1))
    print(k, 'nq', nq, 'gates', ng, 'time', dt, flush=True)
    # compare to target column
    V = T['step']
    # amplitudes at data states with clean ancilla: index = data bits only (ancilla bits 0) -> indices < 2^16 with ancilla bits zero
    amp = sv[:1<<16]
    out_w = np.sum(np.abs(sv)**2) - np.sum(np.abs(amp[T['codes']])**2)
    M = amp[T['codes']]
    tr = np.vdot(V[:, c], M); ph = tr/abs(tr)
    print('   err col', np.abs(M - ph*V[:, c]).max(), 'weight outside code/clean', out_w, flush=True)
    if nq >= 26: break
