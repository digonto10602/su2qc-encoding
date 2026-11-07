import sys, time, json, importlib.util
import numpy as np
spec_ = importlib.util.spec_from_file_location('eng', 'results/rishon/tester-217-engine.py'); eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE
s = rishon_spec('step')
T = eng.algebra_targets(0.37, 0.61)
mod = LE.load_program('compress/programs/rishon/seed/000-general.py')
qc = mod.build(s).circuit()
ops = eng.lower(qc)
qs = eng.used_qubits(ops)
anc = [q for q in qs if q >= 48]
ai = [qs.index(q) for q in anc]
sim = eng.Sim(T['codes'], qs)
n = sim.n
conc = np.zeros(len(T['codes']), int); ever = np.zeros((len(T['codes']), len(anc)), bool)
for op in ops:
    if op[0]=='phase': continue
    sim.apply(*op[:3])
    col = sim.key >> n
    st = sim.key & ((1<<n)-1)
    ab = np.zeros((len(col),), np.int64)
    # per column: OR of ancilla bits -> number of ancilla currently nonzero in at least one branch
    per = np.zeros((len(T['codes']), len(anc)), bool)
    for j,p in enumerate(ai):
        np.logical_or.at(per[:,j], col, ((st>>p)&1).astype(bool))
    ever |= per
    conc = np.maximum(conc, per.sum(1))
print('per-column max concurrent live ancillas (any branch): hist', np.bincount(conc))
print('ever-live ancillas per column hist', np.bincount(ever.sum(1)))
np.save('results/rishon/tester-217-conc.npy', conc)
