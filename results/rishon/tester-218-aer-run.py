"""Driver: Aer statevector check with macro-level liveness.  usage: tester-218-aer-run.py <cid> <alpha> <beta> <nqmin> <nqmax> <nworkers> <out.npz> [max_codes] [seed]
codes are selected by nq = 16 + (ancillas ever non-zero at macro level); stratified random sample if more than max_codes."""
import sys, time, json, importlib.util, os
import numpy as np
from multiprocessing import Pool
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
A = imp("aer218", "tester-218-aer.py"); C = imp("c218", "tester-218-common.py"); eng = A.eng
from su2plaq.rishon.compress.spec import rishon_spec

cid, alpha, beta, nqmin, nqmax, nw, outf = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
maxc = int(sys.argv[8]) if len(sys.argv) > 8 else 10**9
seed = int(sys.argv[9]) if len(sys.argv) > 9 else 218
s = rishon_spec('step').with_angles(alpha, beta)
T = eng.algebra_targets(alpha, beta)
qc = C.build_circuit(cid, s)
anc, ever, used = A.live_sets_macro(qc, T)
nq_all = 16 + ever.sum(1)
sel = [int(c) for c in np.flatnonzero((nq_all >= nqmin) & (nq_all <= nqmax))]
rng = np.random.default_rng(seed)
if len(sel) > maxc:
    sel = sorted(rng.choice(sel, size=maxc, replace=False).tolist())
sel.sort(key=lambda c: -nq_all[c])
print(cid, 'selected', len(sel), 'codes of', len(nq_all), '; nq hist', dict(zip(*np.unique(nq_all[sel], return_counts=True))), flush=True)
jobs = [(qc, int(T['codes'][c]), [anc[j] for j in range(len(anc)) if ever[c, j]], 1) for c in sel]
def work(i):
    return A.run_code(jobs[i])

res_cols, nq_l, tm = {}, {}, {}
t0 = time.time()
with Pool(nw) as pool:
    for i, (code, sv, nq, dt, ng, ndrop, ndiag) in enumerate(pool.imap_unordered(work, range(len(jobs)), chunksize=1)):
        c = int(np.searchsorted(T['codes'], code))
        amp = sv[:1 << 16]
        res_cols[c] = amp[T['codes']].copy()
        out_w = float(np.sum(np.abs(sv) ** 2) - np.sum(np.abs(res_cols[c]) ** 2))
        nq_l[c] = nq; tm[c] = (dt, out_w, ndrop, ndiag)
        if i % 100 == 0:
            print(i, len(jobs), 'nq', nq, 'dt %.1f' % dt, 'elapsed %.0f' % (time.time() - t0), flush=True)
cols = sorted(res_cols)
M = np.array([res_cols[c] for c in cols]).T
V = T['step'][:, cols]
tr = np.trace(V.conj().T @ M); ph = tr / abs(tr)
E = M - ph * V
colerr = np.abs(E).max(0); colnorm2 = np.linalg.norm(E, axis=0)
w_out = np.array([tm[c][1] for c in cols])
np.savez(outf, cols=np.array(cols), nq=np.array([nq_l[c] for c in cols]), colerr_max=colerr, colerr_l2=colnorm2, w_out=w_out, phase=ph, seconds=np.array([tm[c][0] for c in cols]),
         ndrop=np.array([tm[c][2] for c in cols]), ndiag=np.array([tm[c][3] for c in cols]), alpha=alpha, beta=beta)
print('DONE', cid, 'ncols', len(cols), 'qubit hist', {int(k): int(v) for k, v in zip(*np.unique([nq_l[c] for c in cols], return_counts=True))}, 'max col maxabs err %.2e' % colerr.max(),
      'max col L2 err %.2e' % colnorm2.max(), 'max weight outside %.2e' % np.abs(w_out).max(), 'phase', ph, 'cpu-seconds %.0f' % sum(v[0] for v in tm.values()), 'wall %.0f' % (time.time() - t0))
