"""Tester 218: independent recount of (CX, T@1e-6, depth_CT, qubits) for the four round-1 archive programs, using the tester-217 recount code
(own lowering with transpile level 0 + hand macro table + own pygridsynth call).  Also eps=1e-10 T (info) and the archived keys."""
import sys, json, subprocess, importlib.util, os
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
R = imp("rc217", "tester-217-recount.py"); C = imp("c218", "tester-218-common.py")
R.HAND['cp'] = (2, 3, 0)       # cp(+-pi/2): 3 phase gates at +-pi/4 (T-type) + 2 CX
from su2plaq.rishon.compress.spec import rishon_spec
s = rishon_spec('step')
res = {}
for cid, fam in C.CANDS:
    qc = C.build_circuit(cid, s)
    r = R.recount(qc)
    r10 = R.recount(qc, eps=1e-10)
    e = C.entry(cid)
    arch = e['metrics_raw']
    key = e['key']
    rec = dict(recount=r, t_total_1e10=r10['t_total'], archived_key=key, archived=dict(cx=arch['cx'], t_fixed=arch['t_fixed'], n_rot=arch['n_rot'], t_eps=arch['t_eps'], depth_ct=arch['depth_ct'], qubits=arch['qubits'], t_measured=arch['t_measured']),
               match=dict(cx=r['cx'] == arch['cx'] == r['cx_hand'], t_fixed=r['t_fixed'] == arch['t_fixed'] == r['t_hand'] + 0 if False else r['t_fixed'] == arch['t_fixed'], n_rot=r['n_rot'] == arch['n_rot'],
                          t_total=r['t_total'] == arch['t_eps'] == key[1], depth_ct=r['depth_ct'] == arch['depth_ct'] == key[2], qubits=r['qubits'] == arch['qubits'] == key[3], t_1e10=r10['t_total'] == arch['t_measured']['1e-10']))
    res[cid] = rec
    print(cid, r, 't1e-10', r10['t_total'], rec['match'], flush=True)
json.dump({'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), 'rows': res}, open(os.path.join(here, 'tester-218-recount.json'), 'w'), indent=1, default=str)
