"""Tester 220: robustness of T at eps=1e-6 over the seeded 20-pair set (prompts/104 sec.11 E3 of the spinnet clone):
rng = numpy.random.default_rng(20261107); alpha = rng.uniform(0.05, 2.0, 20) THEN beta = rng.uniform(0.05, 1.2, 20).
Own recount (tester-217-recount.py: own lowering + own pygridsynth call) at every pair, plus the production metrics() at every pair for the two named programs.
Also: skeleton identical at all pairs; rotation angles in units of pi/4 (are there angles within 1e-9 of a multiple of pi/4 = free, T-count-reduced?)"""
import sys, os, json, math, subprocess, importlib.util
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
R = imp("rc217", "tester-217-recount.py"); C = imp("c220", "tester-221-common.py")
R.HAND['cp'] = (2, 3, 0)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress.metrics import metrics as prod_metrics
rng = np.random.default_rng(20261107)
alpha = rng.uniform(0.05, 2.0, 20); beta = rng.uniform(0.05, 1.2, 20)
pairs = list(zip(alpha.tolist(), beta.tolist()))
s0 = rishon_spec('step')
cid_list = sys.argv[1:] or [c for c, f in C.CANDS]
out = {}
for cid in cid_list:
    prog = None
    nom = R.recount(C.build_circuit(cid, s0))
    rows = []
    sk0 = None
    for k, (a, b) in enumerate(pairs):
        qc = C.build_circuit(cid, s0.with_angles(a, b))
        sk = [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
        if sk0 is None: sk0 = sk
        r = R.recount(qc)
        row = dict(k=k, alpha=a, beta=b, skeleton_equal=(sk == sk0), cx=r['cx'], t_total=r['t_total'], t_fixed=r['t_fixed'], t_rot=r['t_rot'], n_rot=r['n_rot'], depth_ct=r['depth_ct'], qubits=r['qubits'])
        if cid in ('r04-F3-003', 'r04-F1-004'):
            pm = prod_metrics(qc, s0, measured=True)
            row['prod_t_eps'] = pm['t_eps']; row['prod_cx'] = pm['cx']; row['prod_depth_ct'] = pm['depth_ct']
        rows.append(row)
        print(cid, k, round(a, 4), round(b, 4), row, flush=True)
    T = np.array([r['t_total'] for r in rows]); D = np.array([r['depth_ct'] for r in rows])
    # angle census at nominal and at the 20 pairs: parameters of rz/p in units of pi/4, distance to nearest integer
    qc0 = C.build_circuit(cid, s0)
    ang = [float(i.operation.params[0]) for i in qc0.data if i.operation.name in ('rz', 'p')]
    near = [abs(x / (math.pi / 4) - round(x / (math.pi / 4))) for x in ang]
    names_nonrot = sorted({i.operation.name for i in qc0.data})
    summ = dict(cid=cid, nominal_T=nom['t_total'], nominal_depth_ct=nom['depth_ct'], T_mean=float(T.mean()), T_min=int(T.min()), T_max=int(T.max()), T_std=float(T.std(ddof=1)),
                T_mean_over_nominal=float(T.mean() / nom['t_total']), depth_mean=float(D.mean()), depth_min=int(D.min()), depth_max=int(D.max()),
                cx_all_equal=len({r['cx'] for r in rows}) == 1, cx=rows[0]['cx'], qubits_all_equal=len({r['qubits'] for r in rows}) == 1, n_rot_set=sorted({r['n_rot'] for r in rows}),
                skeleton_equal_all=all(r['skeleton_equal'] for r in rows), production_equals_recount=all(r.get('prod_t_eps', r['t_total']) == r['t_total'] and r.get('prod_cx', r['cx']) == r['cx'] and r.get('prod_depth_ct', r['depth_ct']) == r['depth_ct'] for r in rows),
                nominal_rot_angles_over_pi4=[x / (math.pi / 4) for x in ang], min_distance_to_multiple_of_pi4=float(min(near)), n_rot_params_within_1em9_of_pi4_multiple=int(sum(n < 1e-9 for n in near)),
                gate_names=names_nonrot)
    out[cid] = dict(summary=summ, rows=rows)
    print('SUMMARY', json.dumps(summ), flush=True)
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), seed=20261107, alpha=alpha.tolist(), beta=beta.tolist(), eps=1e-6, programs=out),
          open(os.path.join(here, 'tester-221-robust.json'), 'w'), indent=1)
