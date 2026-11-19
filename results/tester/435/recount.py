"""Independent recount of results/rishon/m6-compressed.json (tester 435). Seed: none (deterministic)."""
import json, hashlib, math, sys, io
from pathlib import Path
import mpmath
from qiskit import qpy
from pygridsynth.gridsynth import gridsynth_gates
R = Path('.')
out = {}; checks = []
def chk(name, expected, got, tol=0.0):
    ok = (abs(expected-got) <= tol) if isinstance(expected,(int,float)) and isinstance(got,(int,float)) else expected == got
    checks.append(dict(check=name, expected=expected, got=got, tol=tol, ok=bool(ok)))
    print(('PASS' if ok else 'FAIL'), name, expected, got)
res = json.load(open('results/rishon/m6-compressed.json'))
chk('provenance.git_dirty', False, res['provenance']['git_dirty'])
chk('circuit_id', 'r06-F3-006', res['circuit_id'])
chk('provenance.git_commit', 'fcd61dd', res['provenance']['git_commit'])
# archive entries
def ent(i): return json.load(open(f'compress/archive/rishon/entries/{i}.json'))
for eid, cx, t in [('r00-seed-000',10102,20650),('r00-seed-001',6874,17694),('r06-F3-006',216,832)]:
    e = ent(eid); chk(f'archive {eid} cx', cx, e['key'][0]); chk(f'archive {eid} T', t, e['key'][1])
    chk(f'archive {eid} valid', True, e['valid'])
# program sha from file
p = R/'compress/programs/rishon/F3/006-closed-mark-in-restore.py'
sha = hashlib.sha256(p.read_bytes()).hexdigest()
chk('program file sha == archive entry sha', ent('r06-F3-006')['program_sha256'], sha)
chk('program sha == m6-compressed headline sha', res['extra']['headline']['program_sha256'], sha)
# round files
rd = {i: json.load(open(f'results/compress/rishon/round-00{i}.json')) for i in range(7)}
out['round_keys'] = {i: rd[i].get('best_key') for i in rd}
print('round best keys', out['round_keys'])
# three-layer
t = json.load(open('results/compress/rishon/three-layer.json'))
chk('three-layer entry', 'r06-F3-006', t['entry']); chk('three-layer sha == archive', ent('r06-F3-006')['program_sha256'], t['program_sha256'])
chk('three-layer unit_key', [216,832,1350,52], t['unit_key'])
chk('three-layer det_key', [32,496,326,48], t['det_key'])
chk('three-layer key', [248,1328,1676,52], t['three_layer_key'])
chk('three-layer git_dirty', False, t['provenance']['git_dirty'])
u, d3, k = t['unit_key'], t['det_key'], t['three_layer_key']
chk('additivity CX', u[0]+d3[0], k[0]); chk('additivity T', u[1]+d3[1], k[1]); chk('additivity depth', u[2]+d3[2], k[2]); chk('qubits = max', max(u[3],d3[3]), k[3])
chk('T mean additivity', round(t['unit_t_mean']+t['det_t_mean'],1), t['three_layer_t_mean'], 1e-6)
chk('three-layer all verdicts ok', True, all(v['ok'] and v['certified'] for v in t['verdicts']))
chk('three-layer 3 triples verdicts', 3, len(t['verdicts']))
# robust.json
rb = json.load(open('results/compress/rishon/robust.json'))
ents = rb['entries']
chk('robust.json has headline entry', True, 'r06-F3-006' in ents)
r = ents['r06-F3-006']; print({kk: (vv if not isinstance(vv,(list,dict)) else '...') for kk,vv in r.items()})
# qpy
with open('results/rishon/m6-compressed.qpy','rb') as f: qc = qpy.load(f)[0]
chk('qpy sha256', res['files']['sha256'], hashlib.sha256(Path('results/rishon/m6-compressed.qpy').read_bytes()).hexdigest())
ops = qc.count_ops(); print(dict(ops))
chk('qpy qubits', 52, qc.num_qubits)
from qiskit import transpile
low = transpile(qc, basis_gates=['cx','h','s','sdg','t','tdg','x','z','rz','p','sx'], optimization_level=0, seed_transpiler=20261104)
lo = dict(low.count_ops()); print('lowered', lo)
chk('lowered cx', 216, lo.get('cx',0))
tf = lo.get('t',0)+lo.get('tdg',0); chk('lowered T_fixed', 196, tf)
# rotations -> pygridsynth
angles = []
for inst in low.data:
    if inst.operation.name in ('rz','p'): angles.append(float(inst.operation.params[0]))
print('rot angles', angles)
chk('n_rot', 10, len(angles))
def tcount(th, eps=1e-6):
    if abs(th/(math.pi/4) - round(th/(math.pi/4))) < 1e-12: return {0:0,1:1,2:0,3:1,4:0,5:1,6:0,7:1}[round(th/(math.pi/4))%8]
    w = str(gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps)))); return w.count('T')
tr = [tcount(a) for a in angles]
chk('sum T_rot pygridsynth eps=1e-6', 636, sum(tr)); chk('T total', 832, tf+sum(tr))
out['T_rot'] = tr
# before/after md and json ratios
ba = {row['row']: row for row in res['extra']['before_after']}
want = {'general':(10102,20650),'general+det':(10134,21146),'cheapest_valid_seed':(6874,17694),'cheapest_valid_seed+det':(6906,18190),'headline':(216,832),'det_layer':(32,496),'headline+det':(248,1328),'global_best+det':(248,1328)}
for kk,(cx,tt) in want.items():
    chk(f'before_after {kk} cx', cx, ba[kk]['cx']); chk(f'before_after {kk} T', tt, ba[kk]['t_1e-6'])
chk('headline T_avg', 829.8, ba['headline']['t_avg'])
print({kk: ba['headline'][kk] for kk in ba['headline'] if kk.startswith('t_') or 'depth' in kk or kk=='qubits'})
chk('headline depth_ct', 1350, res['metrics']['compress_metrics']['depth_ct']); chk('headline qubits', 52, res['metrics']['compress_metrics']['qubits'])
rbj = ents['r06-F3-006']; chk('robust T_sum/20', 829.8, round(rbj['t_sum']/20,1), 1e-9)
udj=json.load(open('results/rishon/UD.json')); chk('UD.json cx/T', [32,496], [udj['metrics']['logical']['cx'], udj['metrics']['t_table'][1]['t_total']])
for nm,cx,tt in [('step',10102,20650),('step3',10134,21146)]:
    j=json.load(open(f'results/rishon/{nm}.json')); chk(f'results/rishon/{nm}.json cx/T', [cx,tt], [j['metrics']['logical']['cx'], j['metrics']['t_table'][1]['t_total']])
dj=res['extra']['det_layer']; chk('det t_sum/20', 500.8, round(dj['t_sum']/20,1), 1e-9)
# md
md = Path('results/rishon/m6-before-after.md').read_text()
import re
rows = {}
for ln in md.splitlines():
    c=[x.strip() for x in ln.strip('|').split('|')]
    if len(c)>=13 and c[0] in want: rows[c[0]] = c
for kk,(cx,tt) in want.items():
    chk(f'md {kk} cx/T', [str(cx),str(tt)], [rows[kk][4], rows[kk][7]])
chk('md headline T_avg', '829.8', rows['headline'][8]); chk('md headline depth', '1350', rows['headline'][11]); chk('md headline qubits','52',rows['headline'][3])
chk('md det T_avg', '500.8', rows['det_layer'][8]); chk('md det depth','326',rows['det_layer'][11]);chk('md 3layer T_avg','1330.6',rows['headline+det'][8]); chk('md 3layer depth','1676',rows['headline+det'][11])
# ratios
for nm,(a,b) in {'CX general/headline':(10102,216),'T general/headline':(20650,832),'CX cheapest/headline':(6874,216),'T cheapest/headline':(17694,832),'CX 3layer general+det/headline+det':(10134,248),'T 3layer':(21146,1328)}.items():
    out.setdefault('ratios',{})[nm]=round(a/b,2)
print(out['ratios'])
out['checks']=checks
import subprocess
out['commit']=subprocess.check_output(['git','rev-parse','--short','HEAD']).decode().strip()
json.dump(out, open('results/tester/435/recount.json','w'), indent=1)
print('FAILS', [c['check'] for c in checks if not c['ok']])
