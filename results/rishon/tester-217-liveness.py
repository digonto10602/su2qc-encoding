import sys, time, json, importlib.util
import numpy as np
spec_ = importlib.util.spec_from_file_location('eng', 'results/rishon/tester-217-engine.py'); eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE
s = rishon_spec('step')
T = eng.algebra_targets(0.37, 0.61)
for name in ['000-general','001-general-rccx','002-general-mcx']:
    mod = LE.load_program(f'compress/programs/rishon/seed/{name}.py')
    qc = mod.build(s).circuit()
    ops = eng.lower(qc)
    qs = eng.used_qubits(ops)
    anc = [q for q in qs if q >= 48]
    amask = sum(1<<qs.index(q) for q in anc)
    sim = eng.Sim(T['codes'], qs); sim.run(ops, amask)
    live = np.array([[ (l>>qs.index(q))&1 for q in anc] for l in sim.live])  # post-gate nonzero flags
    conc = live.sum(1)
    print(name, 'gates', len(ops), 'anc', len(anc), 'max concurrent live ancillas', conc.max(), 'ever live', live.any(0).sum())
