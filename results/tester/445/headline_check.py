"""Tester 445: independent check of the LSH M8 headline from results/lsh/m8-headline-step.qpy.
Reuses the tester-444 own sparse engine / own 24-bit codes / own expm target (results/tester/444/own_sparse.py, imported, not modified).
Deterministic; no RNG (seed null). Run: PYTHONPATH=src taskset -c 0-7 python results/tester/445/headline_check.py"""
import json, sys, hashlib, subprocess, time, pathlib, math
import numpy as np
sys.path.insert(0, 'results/tester/444')
import own_sparse as O
from qiskit import qpy, transpile
ROOT = pathlib.Path('/home/digimonk/Projects/su2qc-encoding')
res = json.load(open(ROOT/'results/lsh/m8-compressed.json'))
checks = []
def chk(name, exp, got, tol=0.0):
    ok = (abs(exp-got) <= tol) if isinstance(exp,(int,float)) and not isinstance(exp,bool) and isinstance(got,(int,float)) else exp == got
    checks.append(dict(check=name, expected=exp, got=got, tol=tol, ok=bool(ok))); print('PASS' if ok else 'FAIL', name, exp, got, flush=True)
qp = ROOT/'results/lsh/m8-headline-step.qpy'
chk('qpy sha256 == json files.sha256', res['files']['sha256'], hashlib.sha256(qp.read_bytes()).hexdigest())
with open(qp,'rb') as f: qc = qpy.load(f)[0]
chk('qpy qubits', 24, qc.num_qubits)
ops = dict(qc.count_ops()); print('native ops', ops)
low = O.lower(qc); lo = dict(low.count_ops()); print('lowered', lo)
rec = O.count(qc)
chk('own CX', 68, rec['cx']); chk('own T_fixed', 24, rec['t_fixed']); chk('own N_rot', 22, rec['n_rot'])
chk('own T total eps 1e-6', 1396, rec['t_total'])
chk('own T total eps 1e-6 == json t_table', [r for r in res['metrics']['t_table'] if r['eps']==1e-6][0]['t_total'], rec['t_total'])
for e in (1e-4, 1e-8, 1e-10):
    r = O.count(qc, eps=e); jr = [x for x in res['metrics']['t_table'] if abs(x['eps']-e)<1e-15]
    print('eps', e, r['t_total'], [x['t_total'] for x in jr]);
    if jr: chk(f'T(eps={e}) own vs json', jr[0]['t_total'], r['t_total'])
out_t = {str(e): O.count(qc, eps=e)['t_total'] for e in (1e-4,1e-6,1e-10)}
# nominal angle verification
a, b = 0.37, 0.61
V = O.target(a, b)
t0=time.time(); Mn, sn = O.block(O.gates_of(qc)); en, ph = O.dist(Mn, V)
Ml, sl = O.block(O.gates_of(low)); el, _ = O.dist(Ml, V)
Vm = O.target(a, -b); ew, _ = O.dist(Mn, Vm)
unit = float(np.linalg.norm(Mn.conj().T @ Mn - np.eye(433), 2))
chk('native 433-state op-norm error < 1e-10', True, en < 1e-10); chk('lowered err < 1e-10', True, el < 1e-10)
chk('native err vs json op_norm_error (both <1e-10)', True, abs(en - res['verification']['op_norm_error']) < 1e-10)
chk('leak 0', True, sn['leak'] < 1e-20); chk('dirty ancilla 0', True, sn['dirty'] < 1e-20)
chk('outer register unchanged', True, sn['outer'] < 1e-20); chk('Abelian Gauss residual 0', True, sn['gauss'] < 1e-20)
chk('wrong-sign target distinguishable (err vs -beta > 0.1)', True, ew > 0.1)
chk('unitarity defect of 433 block < 1e-10', True, unit < 1e-10)
print(dict(en=en, el=el, ew=ew, unit=unit, sn=sn, sl=sl, phase=str(ph), s=time.time()-t0))
# program-built circuit must equal qpy circuit gate for gate
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
prog = ROOT/'compress/programs/lsh/F3/005-alpha-early-walk22.py'
ent = json.load(open(ROOT/'compress/archive/lsh/entries/r05-F3-005.json'))
chk('program sha == archive', ent['program_sha256'], hashlib.sha256(prog.read_bytes()).hexdigest())
qc2 = E.load_program(str(prog)).build(LL.spec()).circuit()
g1, g2 = O.gates_of(qc), O.gates_of(qc2)
chk('qpy gate list == program-built gate list', True, g1 == g2 or all(x[0]==y[0] and x[1]==y[1] and np.allclose(x[2],y[2]) for x,y in zip(g1,g2)) and len(g1)==len(g2))
chk('archive key', [68,1396,3210,24], ent['key'])
json.dump(dict(commit=subprocess.check_output(['git','rev-parse','--short','HEAD'],text=True).strip(), seed=None, pair=[a,b],
  native_ops=ops, lowered_ops=lo, own_count=rec, T_by_eps=out_t, err_native=en, err_lowered=el, err_wrong_sign=ew, unitarity_defect=unit,
  stats_native=sn, stats_lowered=sl, checks=checks, all_ok=all(c['ok'] for c in checks)), open(ROOT/'results/tester/445/headline_check.json','w'), indent=1, default=str)
print('ALL OK' if all(c['ok'] for c in checks) else 'SOME FAIL', sum(c['ok'] for c in checks), '/', len(checks))
