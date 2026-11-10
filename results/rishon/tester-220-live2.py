import sys, json, importlib.util, os
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
A = imp("aer220", "tester-220-aer.py"); C = imp("c220", "tester-220-common.py"); eng = A.eng
from su2plaq.rishon.compress.spec import rishon_spec
s = rishon_spec('step')
T = eng.algebra_targets(s.alpha, s.beta)
out = {}
for cid, fam in C.CANDS:
    qc = C.build_circuit(cid, s)
    anc, ever, used = A.live_sets_macro(qc, T)
    nl = ever.sum(1); nq = 16 + nl
    hist = {int(k): int(v) for k, v in zip(*np.unique(nq, return_counts=True))}
    out[cid] = dict(n_anc_alloc=len(anc), hist_nq=hist, n_le24=int((nq <= 24).sum()), n_le26=int((nq <= 26).sum()), total=len(nq), max_nq=int(nq.max()))
    print(cid, 'macro-level liveness; ancillas', len(anc), 'hist', hist, '<=24:', out[cid]['n_le24'], flush=True)
    np.save(os.path.join(here, f'tester-220-live2-{cid}.npy'), ever)
json.dump(out, open(os.path.join(here, 'tester-220-live2.json'), 'w'), indent=1)
