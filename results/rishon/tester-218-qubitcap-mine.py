"""Tester 218: padded F5 circuits (51+K qubits, K pad ancillas live: CX(0,q) compute/uncompute) on MY sparse engine (compacts the used qubits): 80-qubit circuit is exact."""
import sys, os, json, importlib.util, time
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = imp("c218", "tester-218-common.py"); eng = C.load_engine()
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE
s = rishon_spec('step'); T = eng.algebra_targets(s.alpha, s.beta)
out = {}
for K in (11, 12, 13, 29):
    qc = LE.load_program(sys.argv[1] + f"/padded_{K}.py").build(s).circuit()
    ops = eng.lower(qc); qs = eng.used_qubits(ops)
    sim = eng.Sim(T['codes'], qs); sim.run(ops)
    M, wd, wo = sim.block(T['codes'], list(range(16)))
    ph, e2, _ = eng.compare(M, T['step'])
    out[K] = dict(num_qubits=qc.num_qubits, used=len(qs), block_err=e2, leak=float(np.sqrt((wd + wo).max())), cx=sum(1 for o in ops if o[0] != 'phase' and len(o[0]) == 1 and o[3] == 'cx'))
    print(K, out[K], flush=True)
json.dump(out, open(os.path.join(here, 'tester-218-qubitcap-mine.json'), 'w'), indent=1)
