import sys, json, importlib.util, hashlib, pathlib, time
sys.path.insert(0,'/home/digimonk/Projects/su2qc-encoding/results/tester/439')
import own_sparse as O
import numpy as np
from qiskit import qpy, qasm3
ROOT=pathlib.Path('/home/digimonk/Projects/su2qc-encoding')
d=json.load(open(ROOT/'scratch/m8trial440/m8-compressed.json'))
hid=d['extra']['headline']['id']
ent=json.load(open(ROOT/f'compress/archive/lsh/entries/{hid}.json'))
path=ROOT/ent['program_path']
print('sha file', hashlib.sha256(path.read_bytes()).hexdigest()==ent['program_sha256']==d['extra']['headline']['program_sha256'])
res={}
for (a,b) in O.PAIRS:
    qc=O.E.load_program(str(path)).build(O.LL.spec().with_angles(a,b)).circuit()
    V=O.target(a,b); t0=time.time()
    M,s=O.block(O.gates_of(qc)); e,_=O.dist(M,V)
    Ml,sl=O.block(O.gates_of(O.lower(qc))); el,_=O.dist(Ml,V)
    res[f'{a},{b}']={'native':e,'lowered':el,'stats':s}
    print((a,b),'native',e,'lowered',el,s,time.time()-t0,flush=True)
    if (a,b)==(0.37,0.61):
        # saved circuit file
        with open(ROOT/'scratch/m8trial440/m8-headline-step.qpy','rb') as f: q2=qpy.load(f)[0]
        M2,s2=O.block(O.gates_of(q2)); e2,_=O.dist(M2,V)
        print('qpy file circuit err vs target', e2, s2, 'same gates as rebuilt:', O.gates_of(q2)==O.gates_of(qc))
        q3=qasm3.loads(open(ROOT/'scratch/m8trial440/m8-headline-step.qasm3').read())
        M3,s3=O.block(O.gates_of(O.lower(q3))); e3,_=O.dist(M3,V); print('qasm3 file lowered err', e3, s3)
        print('recount', O.count(qc), 'json logical', d['metrics']['logical'], d['metrics']['gates_lowered'])
        print('own counts at eps list')
        for eps in (1e-4,1e-6,1e-8,1e-10):
            c=O.count(qc,eps); row=next(r for r in d['metrics']['t_table'] if abs(r['eps']-eps)<1e-20)
            print(eps, c['t_total'], row['t_total'], row['t_fixed'],row['n_rot'],row['t_rot_pygridsynth'], c['t_fixed'],c['n_rot'], c['t_total']-c['t_fixed'])
json.dump(res,open('/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/own_head.json','w'))
