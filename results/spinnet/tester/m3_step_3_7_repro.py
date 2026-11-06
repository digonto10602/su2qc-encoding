"""Tester step 3.7: compare a rerun of scripts/m3_results.py (--out DIR) to the committed results/spinnet. usage: repro.py DIR"""
import json, sys, pathlib, hashlib
new = pathlib.Path(sys.argv[1]); old = pathlib.Path('results/spinnet')
SKIP = {'seconds','wall_seconds','peak_rss_mb','timestamp_utc','provenance_captured_at','command','host'}
diffs = []
def cmp(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a)|set(b):
            if k in SKIP: continue
            if k not in a or k not in b: diffs.append((path+'/'+k,'missing')); continue
            cmp(a[k], b[k], path+'/'+k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a)!=len(b): diffs.append((path,'len')); return
        for i,(x,y) in enumerate(zip(a,b)): cmp(x,y,f'{path}[{i}]')
    else:
        if a != b:
            if isinstance(a,str) and isinstance(b,str) and a.replace(str(new),'R')==b.replace(str(old.resolve()),'R'): return
            diffs.append((path, a, b))
for n in ('UE','UB','step'):
    a = json.load(open(old/f'{n}.json')); b = json.load(open(new/f'{n}.json'))
    cmp(a, b, n)
# file-level
fd = []
for p in sorted(old.glob('*.qasm3')):
    q = new/p.name
    fd.append((p.name, 'qasm3', p.read_bytes()==q.read_bytes()))
import qiskit.qpy as qpy
from qiskit.quantum_info import Operator
for p in sorted(old.glob('*.qpy')):
    q = new/p.name
    A = qpy.load(open(p,'rb'))[0]; B = qpy.load(open(q,'rb'))[0]
    fd.append((p.name, 'qpy_bytes', p.read_bytes()==q.read_bytes()))
    fd.append((p.name, 'qpy_ops_equal', A.count_ops()==B.count_ops() and str(A.data)==str(B.data)))
print('JSON diffs (excluding timing/host/command fields):', len(diffs))
for d in diffs[:40]: print(d)
for f in fd: print(f)
