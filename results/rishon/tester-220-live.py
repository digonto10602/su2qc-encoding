"""Tester 219: liveness histogram (per code, number of ancillas ever non-zero) for the four programs at the nominal pair."""
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
    ops = eng.lower(qc); qs = eng.used_qubits(ops)
    anc, ever = A.live_sets(qc, T, ops, qs)
    nl = ever.sum(1)
    nq = 16 + nl
    hist = {int(k): int(v) for k, v in zip(*np.unique(nq, return_counts=True))}
    le24 = int((nq <= 24).sum()); le26 = int((nq <= 26).sum())
    out[cid] = dict(n_anc_alloc=len(anc), qubits_touched=len(qs), hist_nq=hist, n_le24=le24, n_le26=le26, total=len(nq), max_nq=int(nq.max()))
    print(cid, 'ancillas allocated', len(anc), 'hist (16+live)', hist, '<=24:', le24, '<=26:', le26, flush=True)
    np.save(os.path.join(here, f'tester-220-live-{cid}.npy'), ever)
json.dump(out, open(os.path.join(here, 'tester-220-live.json'), 'w'), indent=1)
