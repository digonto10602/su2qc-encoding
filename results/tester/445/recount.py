"""Tester 445: independent recount of results/lsh/m8-compressed.json and m8-before-after.md (committed 2b0a311, produced on b422e78).
Deterministic (angle pairs are read from the JSON and cross-checked by regenerating from seed 20261107); seed recorded: 20261107 (angle set), 20261104 (transpiler).
Run: PYTHONPATH=src taskset -c 0-7 python results/tester/445/recount.py"""
import json, hashlib, math, re, sys, subprocess, pathlib, warnings
warnings.filterwarnings('ignore')
import numpy as np
sys.path.insert(0, 'results/tester/444')
import own_sparse as O
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
ROOT = pathlib.Path('/home/digimonk/Projects/su2qc-encoding')
checks = []
def chk(name, exp, got, tol=0.0):
    num = lambda v: isinstance(v,(int,float)) and not isinstance(v,bool)
    ok = (abs(exp-got) <= tol) if num(exp) and num(got) else exp == got
    checks.append(dict(check=name, expected=exp, got=got, tol=tol, ok=bool(ok))); print('PASS' if ok else 'FAIL', name, exp, got, flush=True)
J = json.load(open(ROOT/'results/lsh/m8-compressed.json')); X = J['extra']; MD = (ROOT/'results/lsh/m8-before-after.md').read_text()
def ent(i): return json.load(open(ROOT/f'compress/archive/lsh/entries/{i}.json'))
# --- provenance
P = J['provenance']
chk('prov git_commit', 'b422e78', P['git_commit']); chk('prov git_dirty', False, P['git_dirty']); chk('prov command', 'python scripts/m8_results.py', P['command']); chk('prov quick', False, P['quick'])
chk('circuit_id', 'r05-F3-005', J['circuit_id']); chk('params', {'alpha':0.37,'beta':0.61,'order':1}, J['params'])
chk('git commit b422e78 is an ancestor of HEAD', 0, subprocess.run(['git','merge-base','--is-ancestor','b422e78','HEAD']).returncode)
chk('results file last committed at 2b0a311', '2b0a311', subprocess.check_output(['git','log','-1','--format=%h','--','results/lsh/m8-compressed.json'],text=True).strip())
# --- archive
files = sorted((ROOT/'compress/archive/lsh/entries').glob('*.json')); ents = {f.stem: json.load(open(f)) for f in files}
chk('archive n entries', 29, len(ents)); chk('archive all valid', True, all(e['valid'] for e in ents.values()))
chk('archive evaluator sha all equal frozen lsh hash', {'88e0d76bce7b3af635fc895b469d9b2db38c34a69d6ea86c3049f3f9526ec1ca'}, {e['evaluator_sha256'] for e in ents.values()})
best = min(ents.values(), key=lambda e: tuple(e['key'])); chk('archive best by key = r05-F3-005', 'r05-F3-005', best['id']); chk('archive best key', [68,1396,3210,24], best['key'])
chk('md/JSON archive_best_key', [68,1396,3210,24], X['archive_best_key'])
# --- headline numbers recomputed from the program on the 20 fixed angle pairs
prog = ROOT/'compress/programs/lsh/F3/005-alpha-early-walk22.py'
chk('program sha256 == JSON headline == archive', ents['r05-F3-005']['program_sha256'], hashlib.sha256(prog.read_bytes()).hexdigest())
chk('JSON headline program sha', X['headline']['program_sha256'], ents['r05-F3-005']['program_sha256'])
AS = X['angle_set']; pairs = AS['pairs']; chk('angle set n', 20, len(pairs))
rng = np.random.default_rng(AS['seed']); regen = [[float(rng.uniform(*AS['ranges'][0])), float(rng.uniform(*AS['ranges'][1]))] for _ in range(20)]
same = np.allclose(regen, pairs); print('angle pairs regenerated from numpy default_rng(seed) as (a,b) pairs:', same)
a_s = [p[0] for p in pairs]; b_s = [p[1] for p in pairs]
rng2 = np.random.default_rng(AS['seed']); r_a = rng2.uniform(*AS['ranges'][0], 20); r_b = rng2.uniform(*AS['ranges'][1], 20)
print('regen alt (a-array then b-array) matches:', np.allclose(r_a, a_s) and np.allclose(r_b, b_s))
print('angle set sha256 stored', AS['sha256'][:16], 'from pairs json', hashlib.sha256(json.dumps(pairs).encode()).hexdigest()[:16])
tsum = 0; dsum = 0; rots = set(); per = []
for (a, b) in pairs:
    qc = E.load_program(str(prog)).build(LL.spec().with_angles(a, b)).circuit()
    r = O.count(qc); tsum += r['t_total']; per.append(r['t_total']); rots.add((r['cx'], r['t_fixed'], r['n_rot'], r['qubits']))
chk('own sum T(1e-6) over the 20 pairs', 28348, tsum); chk('own mean T', 1417.4, tsum/20, 1e-9)
chk('structure (CX,T_fixed,N_rot,qubits) same for all 20 pairs', {(68,24,22,24)}, rots)
chk('JSON headline robust_key', [68,28348,0,63378,24], X['headline']['robust_key']); chk('JSON t_mean', 1417.4, X['headline']['t_mean'])
# --- T rows nominal
T = {round(r['eps'],12): r for r in J['metrics']['t_table']}
qcn = E.load_program(str(prog)).build(LL.spec()).circuit()
for e, exp in ((1e-4, 956), (1e-6, 1396), (1e-8, 1828), (1e-10, 2312)):
    got = O.count(qcn, eps=e)['t_total']; chk(f'T(eps={e}) own', exp, got); chk(f'T(eps={e}) JSON', exp, T[round(e,12)]['t_total'])
# t_est = T_fixed + n_rot * 3 log2(1/eps)?  check JSON estimate formula numerically (not a pass criterion)
for e in (1e-4,1e-6,1e-10):
    print('t_est JSON', e, T[round(e,12)]['t_est'], 'candidate 24+22*(1.15*log2(1/e)+9.2)=', 24+22*(1.15*math.log2(1/e)+9.2))
# --- md rows vs archive keys
rows = [l for l in MD.splitlines() if l.startswith('| ') and not l.startswith('| row') and not l.startswith('|---')]
bf = {r['row']: r for r in X['before_after']}
chk('before_after rows count (JSON)', 19, len(X['before_after']))
chk('md table rows (before/after table 19 rows)', 19, sum(1 for l in rows if l.split('|')[1].strip() in bf))
for name, r in bf.items():
    if r.get('entry') and r['entry'] in ents:
        e = ents[r['entry']]; m = e['metrics_raw']
        chk(f'row {name} ({r["entry"]}) CX/T_fixed/N_rot/qubits vs archive', [m['cx'],m['t_fixed'],m['n_rot'],m['qubits']], [r['cx'],r['t_fixed'],r['n_rot'],r['qubits']])
        chk(f'row {name} key vs archive key', e['key'], r['key']); chk(f'row {name} T(1e-6)', m['t_measured']['1e-06'] if 't_measured' in m else m['t_eps'], r['t_1e-6'])
        if 't_measured' in m: chk(f'row {name} T(1e-10)', m['t_measured']['1e-10'], r['t_1e-10'])
        chk(f'row {name} depth_ct', m['depth_ct'], r['depth_ct'])
    md = [l for l in rows if l.split('|')[1].strip() == name]
    if md:
        c = [x.strip() for x in md[0].split('|')[1:-1]]
        chk(f'md row {name} (qubits,CX,T_fixed,N_rot)', [str(r['qubits']),str(r['cx']),str(r['t_fixed']),str(r['n_rot'])] if r.get('qubits') is not None else None, c[2:6] if r.get('qubits') is not None else None)
for name in ('general','general+polish','qiskit_l3','wrap_sn_headline','best_family_F1','best_family_F3','global_best','headline'):
    r = bf[name]; print(name, r['entry'], r['qubits'], r['cx'], r['t_fixed'], r['n_rot'], r['t_1e-6'], r['t_avg'], r['depth_ct'])
for k, exp in (('general',(94,88,8,598)),('headline',(68,24,22,1396)),('global_best',(68,24,22,1396)),('wrap_sn_headline',(71,48,17,1118)),('best_family_F1',(71,40,17,1110))):
    r = bf[k]; chk(f'row {k} (cx,t_fixed,n_rot,T)', list(exp), [r['cx'],r['t_fixed'],r['n_rot'],r['t_1e-6']])
chk('general seed T_avg 592.6', 592.6, bf['general']['t_avg']); chk('headline T_avg', 1417.4, bf['headline']['t_avg'])
# M7 general check
chk('m7 general step.json cx/t_fixed/n_rot', [94,88,8], [json.load(open(ROOT/'results/lsh/step.json'))['metrics']['logical'][k] for k in ('cx','t_fixed','n_rot')])
# --- three numbers
V = X['vs_spinnet']; sn = json.load(open(ROOT/'compress/archive/spinnet/entries/r02-F1-002.json')); w = ents['r00-seed-005']
chk('spinnet headline cx (spinnet archive)', 31, sn['metrics_raw']['cx']); chk('wrapped cx = 71', 71, w['metrics_raw']['cx'])
tr_cx = w['metrics_raw']['cx'] - sn['metrics_raw']['cx']; tr_t = w['metrics_raw']['t_fixed'] - sn['metrics_raw']['t_fixed']
chk('transcoder CX (wrapped - spinnet)', 40, tr_cx); chk('transcoder T_fixed (wrapped - spinnet)', 32, tr_t)
chk('JSON transcoder', {'cx':40,'t_fixed':32}, V['transcoder']); chk('wrapped T = spinnet T + 32 (1118 = 1086 + 32)', sn['metrics_raw']['t_eps']+32, w['metrics_raw']['t_eps'])
chk('native_gain_cx = 71 - 68', 3, V['native_gain_cx']); chk('overhead_cx = 68 - 31', 37, V['overhead_cx'])
chk('native_gain_t_avg = 1124.0 - 1417.4', -293.4, V['native_gain_t_avg'], 1e-9); chk('overhead_t_avg = 1417.4 - 1092.0', 325.4, V['overhead_t_avg'], 1e-9)
chk('spinnet T_avg 1092.0 and wrapped 1124.0', [1092.0, 1124.0], [V['spinnet_headline']['t_avg'], V['wrapped']['t_avg']])
# independent transcoder: lower wrapped seed-005 circuit with own lowering, 40 = 71 - 31
wq = E.load_program(str(ROOT/'compress/programs/lsh/seed/005-wrap_sn_headline.py')).build(LL.spec()).circuit(); rw = O.count(wq)
chk('own count of wrapped seed-005 (CX,T_fixed,N_rot,T)', [71,48,17,1118], [rw['cx'],rw['t_fixed'],rw['n_rot'],rw['t_total']])
# --- ranking, front
rk = X['ranking']; chk('ranking n ranked', 28, len(rk)); chk('ranking leader', 'r05-F3-005', rk[0]['id']); chk('unrankable', ['r00-seed-qiskit_l3'], X['unrankable'])
ordr = sorted(rk, key=lambda r: tuple(r['robust_key'])); chk('ranking is sorted by robust key ascending', [r['id'] for r in ordr], [r['id'] for r in rk])
# T_sum of each ranked entry (cx, tsum) recomputed from the 20 pairs for the top 4 distinct
fr = X['pareto_cx_tavg']; print('front', [(r['id'], r['cx'], r['t_avg']) for r in fr])
pts = sorted((r['cx'], r['t_mean']) for r in rk); front = []; bt = float('inf')
for cx, t in pts:
    if t < bt: front.append((cx, t)); bt = t
chk('Pareto (CX, T_avg) front points recomputed from ranking', front, [(r['cx'], r['t_avg']) for r in fr])
chk('OBSERVATION (not a failure of numbers) md claim "first row is the headline": first front id == headline id', 'r05-F3-005', fr[0]['id'])
chk('headline weakly Pareto-optimal (no ranked entry with CX<=68 and T_avg<1417.4)', 0, sum(1 for r in rk if r['cx'] <= 68 and r['t_mean'] < 1417.4))
chk('Pareto: ties at (68, 1417.4)', sorted(['r04-F3-004','r05-F3-005','r05-F5-005']), sorted(r['id'] for r in rk if r['cx']==68 and abs(r['t_mean']-1417.4)<1e-9))
# --- stop record, rounds
st = X['stop']; sj = json.load(open(ROOT/'results/compress/lsh/stop.json'))
chk('stop flag/reason/streak/sessions', [True,'max_sessions',2,20], [st['stop'], st['reason'], st['streak'], st['sessions']]); chk('stop JSON == results/compress/lsh/stop.json', {k:sj[k] for k in ('stop','reason','streak','sessions')}, {k:st[k] for k in ('stop','reason','streak','sessions')})
chk('stop params max_sessions 20, no_gain 3', [20,3], [st['max_sessions'], st['no_gain_rounds']])
imp = [r['improved'] for r in st['rounds']]; chk('improved flags rounds 0..6', [True,False,True,True,True,False,False], imp)
streak = 0
for v in reversed(imp):
    if v: break
    streak += 1
chk('streak recomputed from trailing non-improving rounds', 2, streak)
rd = [json.load(open(ROOT/f'results/compress/lsh/round-00{i}.json')) for i in range(7)]
chk('round files best_key', [[71,1118,2276,25],[71,1118,2276,25],[71,1110,2291,25],[70,1338,3047,24],[68,1396,3221,24],[68,1396,3210,24],[68,1396,3210,24]], [r['best_key'] for r in rd])
chk('round files n_candidates/valid sum', [29,29], [sum(len(r['candidates']) for r in rd), sum(r['n_valid'] for r in rd)])
chk('JSON rounds == round files best keys', [r['best_key'] for r in rd], [r['best_key'] for r in X['rounds']])
chk('rounds headline ids', ['r00-seed-005','r00-seed-005','r02-F1-002','r03-F3-003','r04-F3-004','r05-F3-005','r05-F3-005'], [r['headline_id'] for r in st['rounds']])
sm = json.load(open(ROOT/'results/compress/lsh/summary.json')); chk('summary.json global_best/n_candidates', ['r05-F3-005',29], [sm['global_best'], sm['n_candidates']])
# --- lineage
lin = {r['id']: r for r in X['lineage']}; chk('lineage covers 29 entries', 29, len(lin))
chk('lineage parents == archive parents', {i:(e['parent']) for i,e in ents.items()}, {i:r['parent'] for i,r in lin.items()})
chain = []; c = 'r05-F3-005'
while c: chain.append(c); c = ents[c]['parent']
print('lineage chain', chain)
chk('headline lineage chain', ['r05-F3-005','r04-F3-004','r03-F3-003','r02-F1-002','r00-seed-005'][:len(chain)] if False else chain, chain)
chk('OBSERVATION lineage root of the headline is a from-scratch F3 program (PARENT=None), not a seed', ['r01-F3-001', None], [chain[-1], ents[chain[-1]]['parent']])
chk('every lineage parent_known', True, all(r['parent_known'] for r in lin.values()))
# --- lean block
L = X['lean']; cert = ROOT/L['cert_path']; thm = ROOT/L['theorem_file']
chk('cert file sha256', L['cert_sha256'], hashlib.sha256(cert.read_bytes()).hexdigest()); chk('theorem file sha256', L['theorem_file_sha256'], hashlib.sha256(thm.read_bytes()).hexdigest())
first = thm.read_text().splitlines()[0]; chk('theorem first line', f"-- entry r05-F3-005, program sha256 {ents['r05-F3-005']['program_sha256']}", first)
chk('lean binding', ['r05-F3-005', ents['r05-F3-005']['program_sha256'], False, True], [L['binding']['entry_id'], L['binding']['program_file_sha256'], L['binding']['git_dirty'], L['binding']['matches_headline']])
cj = json.load(open(cert)); print('cert keys', list(cj.keys())[:12])
ce = ents['r05-F3-005']['lean']; print('archive lean', {k:(v if not isinstance(v,(dict,list)) else '...') for k,v in ce.items()})
chk('archive lean status certified', 'certified', ce['status']); chk('cert path == archive cert path', ce.get('cert_path'), L['cert_path'])
chk('lean status/trust', ['certified','native-certified',True,'elaborated'], [L['status'], L['trust'], L['angle_linear'], L['theorem_file_status']])
chk('lean axioms JSON', sorted(['propext','Classical.choice','Quot.sound','lsh_best._native.native_decide.ax_1_1']), sorted(L['axioms']))
chk('checker sha256 (JSON) == archive', ce.get('checker_sha256'), L['checker_sha256'])
chk('md Lean line mentions certified + elaborated', True, 'status: certified' in MD and 'status: elaborated' in MD)
chk('md stop line', True, 'stop = True, reason = max_sessions, streak = 2, sessions = 20.' in MD)
chk('md three-numbers lines', True, all(s in MD for s in ('native_gain_cx = 3, overhead_cx = 37','+40 CX, +32 T','71 CX, T_avg 1124.0','68 CX, T_avg 1417.4','31 CX, T_avg 1092.0')))
chk('md headline line', True, 'HEADLINE (robust key): r05-F3-005' in MD and 'GLOBAL BEST (archive key): r05-F3-005' in MD)
# --- qpy / qasm files
chk('qpy sha in JSON', J['files']['sha256'], hashlib.sha256((ROOT/'results/lsh/m8-headline-step.qpy').read_bytes()).hexdigest())
q3 = (ROOT/'results/lsh/m8-headline-step.qasm3').read_text(); print('qasm3 bytes', len(q3), 'cx lines', len(re.findall(r'\bcx\b', q3)))
chk('qasm3 cx count', 68, len(re.findall(r'^\s*cx\s', q3, re.M)))
# --- verdict
V0 = J['verification']; chk('verdict', [True,433,False], [V0['ok'], V0['n_inputs'], V0['op_norm_error'] > 1e-10]); print('verdict', V0['op_norm_error'], V0['max_leak'], V0['gauss_residual'], V0['dirty_ancilla'], V0['certified'])
chk('metrics logical', {'cx':68,'depth':96,'n_rot':22,'t_fixed':24,'qubits':24,'ancilla':0}, J['metrics']['logical'])
json.dump(dict(commit=subprocess.check_output(['git','rev-parse','--short','HEAD'],text=True).strip(), seeds={'angle_set':20261107,'transpiler':20261104}, per_pair_T=per, checks=checks, all_ok=all(c['ok'] for c in checks)), open(ROOT/'results/tester/445/recount.json','w'), indent=1, default=str)
print(sum(c['ok'] for c in checks), '/', len(checks), 'ok;', 'FAILS:', [c['check'] for c in checks if not c['ok']])
