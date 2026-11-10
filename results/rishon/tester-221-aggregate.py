import glob, json, os, subprocess
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(here, 'tester-221-aer-r04-*.npz'))):
    d = np.load(f)
    base = os.path.basename(f)[len('tester-221-aer-'):-4]
    cid, tag = base.rsplit('-', 1)
    nq = d['nq']
    rows.append(dict(cid=cid, tag=tag, alpha=float(d['alpha']), beta=float(d['beta']), n_codes=int(len(d['cols'])),
                     nq_hist={int(k): int(v) for k, v in zip(*np.unique(nq, return_counts=True))},
                     max_col_err_maxabs=float(d['colerr_max'].max()), max_col_err_l2=float(d['colerr_l2'].max()),
                     max_weight_outside=float(np.abs(d['w_out']).max()), phase=[float(d['phase'].real), float(d['phase'].imag)],
                     cpu_seconds=float(d['seconds'].sum()), n_dead_gates_dropped_max=int(d['ndrop'].max()), n_diag_replaced_max=int(d['ndiag'].max())))
    print(rows[-1]['cid'], rows[-1]['tag'], (rows[-1]['alpha'], rows[-1]['beta']), rows[-1]['n_codes'], 'nq', min(rows[-1]['nq_hist']), '-', max(rows[-1]['nq_hist']), 'err %.2e L2 %.2e wout %.1e phase_im %.1e cpu %.0f s' % (rows[-1]['max_col_err_maxabs'], rows[-1]['max_col_err_l2'], rows[-1]['max_weight_outside'], rows[-1]['phase'][1], rows[-1]['cpu_seconds']))
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), rows=rows), open(os.path.join(here, 'tester-221-aer-summary.json'), 'w'), indent=1)
