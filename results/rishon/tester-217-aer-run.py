"""Driver: Aer statevector check, columns selected by number of live ancillas.  usage: tester-217-aer-run.py <program> <alpha> <beta> <kmin> <kmax> <nworkers> <out.npz> [max_codes] [stride_seed]"""
import sys, time, json, importlib.util, os
import numpy as np
from multiprocessing import Pool
here = os.path.dirname(os.path.abspath(__file__))
spec_ = importlib.util.spec_from_file_location('aer', os.path.join(here, 'tester-217-aer.py')); aer = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(aer)
eng = aer.eng
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE

prog, alpha, beta, kmin, kmax, nw, outf = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
maxc = int(sys.argv[8]) if len(sys.argv) > 8 else 10**9
s = rishon_spec('step').with_angles(alpha, beta)
T = eng.algebra_targets(alpha, beta)
qc = LE.load_program(prog).build(s).circuit()
ops = eng.lower(qc); qs = eng.used_qubits(ops)
anc, ever = aer.live_sets(qc, T, ops, qs)
nl = ever.sum(1)
sel = [int(c) for c in np.flatnonzero((nl >= kmin) & (nl <= kmax))]
rng = np.random.default_rng(217)
if len(sel) > maxc:
    sel = sorted(rng.choice(sel, size=maxc, replace=False).tolist())
sel.sort(key=lambda c: -nl[c])
print('selected', len(sel), 'codes; hist', np.bincount(nl[sel]), flush=True)
jobs = [(qc, int(T['codes'][c]), [anc[j] for j in range(len(anc)) if ever[c, j]], 1) for c in sel]
def work(i):
    return aer.run_code(jobs[i])


res_cols, nq_l, tm = {}, {}, {}
t0 = time.time()
with Pool(nw) as pool:
    for i, (code, sv, nq, dt, ng) in enumerate(pool.imap_unordered(work, range(len(jobs)), chunksize=1)):
        c = int(np.searchsorted(T['codes'], code))
        amp = sv[:1 << 16]
        res_cols[c] = amp[T['codes']].copy()
        out_w = float(np.sum(np.abs(sv) ** 2) - np.sum(np.abs(res_cols[c]) ** 2))
        nq_l[c] = nq; tm[c] = (dt, out_w)
        if i % 50 == 0:
            print(i, len(jobs), 'nq', nq, 'elapsed %.0f' % (time.time() - t0), flush=True)
cols = sorted(res_cols)
M = np.array([res_cols[c] for c in cols]).T          # [1296, ncols]
V = T['step'][:, cols]
tr = np.trace(V.conj().T @ M); ph = tr / abs(tr)
E = M - ph * V
colerr = np.abs(E).max(0); colnorm2 = np.linalg.norm(E, axis=0)
w_out = np.array([tm[c][1] for c in cols])
np.savez(outf, cols=np.array(cols), nq=np.array([nq_l[c] for c in cols]), colerr_max=colerr, colerr_l2=colnorm2, w_out=w_out, phase=ph, seconds=np.array([tm[c][0] for c in cols]), alpha=alpha, beta=beta)
print('DONE ncols', len(cols), 'qubit hist', dict(zip(*np.unique([nq_l[c] for c in cols], return_counts=True))), 'max col maxabs err %.2e' % colerr.max(),
      'max col L2 err %.2e' % colnorm2.max(), 'max weight outside %.2e' % np.abs(w_out).max(), 'phase', ph, 'wall %.0f' % (time.time() - t0))
