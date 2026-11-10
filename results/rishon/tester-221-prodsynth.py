"""Tester 220: production verify_synthesised (read-only call) on the three programs, components of the verdict, for comparison with my own Clifford+T verification."""
import sys, json, importlib.util, os, subprocess
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("c220", os.path.join(here, "tester-221-common.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress.evaluate import verify_synthesised
s = rishon_spec('step'); out = {}
for cid, f in C.CANDS:
    qc = C.build_circuit(cid, s)
    r = verify_synthesised(qc, s, 1e-6)
    v = r['verdict']
    out[cid] = dict(ok=r['ok'], n_rot=r['n_rot'], t_total=r['t_total'], tol=r['tolerances'], error_bound_sum=r['error_bound_sum'], error_measured_sum=r['error_measured_sum'],
                    op=v.op_norm_error, block=v.block_error, leak=v.max_leak, dropped=v.dropped_total, gauss=v.gauss_residual, certified=v.certified, engine=v.engine)
    print(cid, out[cid], flush=True)
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), rows=out), open(os.path.join(here, 'tester-221-prodsynth.json'), 'w'), indent=1, default=str)
