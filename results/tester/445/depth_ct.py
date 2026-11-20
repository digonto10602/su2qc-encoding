"""Tester 445: own Clifford+T depth of the headline: replace each non-Clifford rotation by its pygridsynth word (eps 1e-6), count qiskit depth of
the all-gates circuit; compare to archive depth_ct = 3210 (nominal) and the 20-pair sum 63378.  Also the angle-set sha. Deterministic."""
import json, math, sys, warnings, hashlib, pathlib
warnings.filterwarnings('ignore')
sys.path.insert(0,'results/tester/444')
import numpy as np, pygridsynth
import own_sparse as O
from qiskit import QuantumCircuit, qpy
from su2plaq.compress import evaluate as E, robust as R
from su2plaq.lsh import loop as LL
J = json.load(open('results/lsh/m8-compressed.json')); pairs = J['extra']['angle_set']['pairs']
ANG = tuple((float(x), float(y)) for x, y in pairs)
print('angle-set sha own (repr of locked tuple):', hashlib.sha256(repr(ANG).encode()).hexdigest()[:16], 'stored', J['extra']['angle_set']['sha256'][:16], 'module', R.angle_set_sha256()[:16])
_cache = {}
def word(th, eps):
    k = (round(th, 14), eps)
    if k not in _cache: _cache[k] = str(pygridsynth.gridsynth_gates(theta=th, epsilon=eps))
    return _cache[k]
def depth_ct(qc, eps=1e-6):
    q = O.lower(qc); out = QuantumCircuit(q.num_qubits); tcount = 0
    for ins in q.data:
        nm = ins.operation.name; qs = [q.find_bit(b).index for b in ins.qubits]; ps = [float(x) for x in ins.operation.params]
        if nm in ('rz', 'p', 'u1'):
            th = ps[0]; k = th / (math.pi/4)
            if abs(k - round(k)) < 1e-9:
                for _ in range(int(round(k)) % 8): out.t(qs[0])           # k*pi/4 phase as T^k (global phase ignored)
            else:
                for ch in word(th, eps):
                    {'H': out.h, 'S': out.s, 'T': out.t, 'X': out.x, 'W': lambda *a: None, 'I': lambda *a: None}[ch](qs[0])
        else:
            getattr(out, nm)(*qs)
    return out.depth(), out.num_qubits
prog = pathlib.Path('compress/programs/lsh/F3/005-alpha-early-walk22.py')
qc = E.load_program(str(prog)).build(LL.spec()).circuit()
print('nominal depth_CT own', depth_ct(qc), 'archive 3210')
tot = 0
for a, b in ANG:
    qc = E.load_program(str(prog)).build(LL.spec().with_angles(a, b)).circuit(); tot += depth_ct(qc)[0]
print('sum over 20 pairs own', tot, 'stored 63378')
json.dump({'nominal_depth_own': depth_ct(E.load_program(str(prog)).build(LL.spec()).circuit())[0], 'sum20_own': tot, 'stored': [3210, 63378]}, open('results/tester/445/depth_ct.json','w'))
# tie-break ordering among the three (68, 1396/28348) entries, nominal pair, own depth vs archive depth_ct
import glob
res = {}
for eid, rel in (('r04-F3-004','F3/004-joint-sa-walk22.py'),('r05-F3-005','F3/005-alpha-early-walk22.py'),('r05-F5-005','F5/005-all-pivot-collapse-fold-frame.py')):
    p = pathlib.Path('compress/programs/lsh')/rel
    qc = E.load_program(str(p)).build(LL.spec()).circuit(); d = depth_ct(qc)[0]
    ar = json.load(open(f'compress/archive/lsh/entries/{eid}.json'))['key'][2]
    res[eid] = (d, ar); print(eid, 'own depth', d, 'archive depth_ct', ar)
print('own order', sorted(res, key=lambda k: res[k][0]), 'archive order', sorted(res, key=lambda k: res[k][1]))
json.dump(res, open('results/tester/445/depth_tiebreak.json','w'))
