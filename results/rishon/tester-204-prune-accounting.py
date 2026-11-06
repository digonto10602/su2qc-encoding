"""Tester 204: prune-bound accounting of the production verdict on U_B / step (prompts/005 relative cap 1e-2 tol_err)."""
import sys, json, subprocess, time
sys.path.insert(0, 'src')
import numpy as np
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as Vf
import su2plaq.circuits.rishon as C
from su2plaq.evaluate import evaluator as E
enc = RishonEncoding()
out = {'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip() + '+uncommitted', 'PRUNE_FRACTION': E.PRUNE_FRACTION}
rows = {}
cases = {'UB(0.61)': (C.build_UB(0.61), 'UB', None, 0.61, 1), 'UB(2.0)': (C.build_UB(2.0), 'UB', None, 2.0, 1),
         'step1(0.37,0.61)': (C.build_step(0.37, 0.61, 1), 'step', 0.37, 0.61, 1), 'step2(0.37,0.61)': (C.build_step(0.37, 0.61, 2), 'step', 0.37, 0.61, 2),
         'step2(1.7,1.0)': (C.build_step(1.7, 1.0, 2), 'step', 1.7, 1.0, 2)}
for name, (qc, kind, al, be, order) in cases.items():
    t = time.time()
    v = Vf.verify(qc, enc, kind, al, be, order=order)
    rows[name] = {'ok': v.ok, 'reason': v.reason, 'op_norm_error': v.op_norm_error, 'block_error': v.block_error, 'dropped_total': v.dropped_total,
                  'leak_amplitude': v.leak_amplitude, 'sum_check': abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)),
                  'cap': E.PRUNE_FRACTION * 1e-10, 'headroom': E.PRUNE_FRACTION * 1e-10 / v.dropped_total, 'gauss_residual': v.gauss_residual,
                  'gauss_states': v.gauss_states, 'max_leak': v.max_leak, 'dirty_ancilla': v.dirty_ancilla, 'engine': v.engine, 'certified': v.certified,
                  'seconds': time.time() - t}
    print(name, rows[name], flush=True)
out['verdicts'] = rows
# boundary of the cap rule on U_B(0.61): dropped_total = d.  tol_err just below 100 d must give pruning_bound; just above must be ok.
qc = C.build_UB(0.61); d = rows['UB(0.61)']['dropped_total']
bd = {}
for label, tol in (('0.9*100*d', 0.9 * 100 * d), ('1.1*100*d', 1.1 * 100 * d)):
    v = Vf.verify(qc, enc, 'UB', None, 0.61, tol_err=tol, gauss=False)
    bd[label] = {'tol_err': tol, 'ok': v.ok, 'reason': v.reason, 'dropped_total': v.dropped_total, 'cap': E.PRUNE_FRACTION * tol}
    print(label, bd[label], flush=True)
out['cap_boundary'] = bd
json.dump(out, open('results/rishon/tester-204-prune-accounting.json', 'w'), indent=1, default=str)
