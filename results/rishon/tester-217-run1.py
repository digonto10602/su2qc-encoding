import sys, time, json, importlib.util
import numpy as np
sys.path.insert(0, 'results/rishon')
spec_ = importlib.util.spec_from_file_location('eng', 'results/rishon/tester-217-engine.py'); eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE
s = rishon_spec('step')
t0=time.time()
T = eng.algebra_targets(0.37, 0.61)
print('targets', time.time()-t0, T['he_offdiag'], T['hb_herm'], T['W_real'])
from su2plaq.rishon import operators as O
print('vs inner_target', np.abs(T['step']-O.inner_target('step',0.37,0.61)).max())
mod = LE.load_program('compress/programs/rishon/seed/000-general.py')
qc = mod.build(s).circuit()
ops = eng.lower(qc)
print(len(ops))
qs = eng.used_qubits(ops)
print(qs)
anc_mask = sum(1<<eng.used_qubits(ops).index(q) for q in qs if q>=48)
sim = eng.Sim(T['codes'], qs, thr=1e-15)
t0=time.time(); sim.run(ops, anc_mask); print('run', time.time()-t0, sim.maxsize)
M, wd, wo = sim.block(T['codes'], list(range(16)))
ph, e2, emax = eng.compare(M, T['step'])
print(ph, e2, emax, np.sqrt(wd.max()), np.sqrt(wo.max()), np.sqrt((sim.dw_sq).sum()), np.sqrt((sim.dw_tri**2).sum()))
