"""Tester 220: exhaustive single-gate mutant battery on the round-3 programs, my sparse engine (../../rishon/tester-217-engine.py), all 1296 codes, nominal pair (0.37, 0.61).
For every gate of the program's (macro-level) circuit:
  drop       delete the gate (every gate of every type except none excluded; 'gauge' = s, sdg, t, tdg, z, cz, ccz)
  tswap      t <-> tdg;  sswap  s <-> sdg
  rccx2ccx   replace a relative-phase Toffoli by the exact Toffoli
  cxswap     cx control/target swapped (a random 12 per program, seed 220)
  angle      rz/p parameter + 1e-6;  flip: parameter sign flipped
Detected = block error > 1e-9 or leak > 1e-9 or the engine raises.  Unmutated baseline ~ 2e-14.
usage: 433-symdel.py <cid> <shard> <nshards>  (mirror-pair deletions: gate j and gate N-1-j, same qubits, same/inverse name)"""
import sys, os, json, importlib.util, time, subprocess
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = imp("c220", "433-common.py"); eng = C.load_engine()
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate
from su2plaq.rishon.compress.spec import rishon_spec
cid = sys.argv[1]
s = rishon_spec('step'); T = eng.algebra_targets(s.alpha, s.beta)
rng = np.random.default_rng(220)
qc = C.build_circuit(cid, s)
data = [(i.operation, [qc.find_bit(q).index for q in i.qubits]) for i in qc.data]
N = len(data)
INV = {'t': 'tdg', 'tdg': 't', 's': 'sdg', 'sdg': 's'}
def rebuild(drop):
    out = QuantumCircuit(qc.num_qubits); out.global_phase = qc.global_phase
    for j, (op, qs) in enumerate(data):
        if j not in drop: out.append(op, qs)
    return out
def run(c):
    try:
        ops = eng.lower(c); qs = eng.used_qubits(ops)
        sim = eng.Sim(T['codes'], qs); sim.run(ops)
        M, wd, wo = sim.block(T['codes'], list(range(16)))
        ph, e2, _ = eng.compare(M, T['step'])
        return float(e2), float(np.sqrt((wd + wo).max()))
    except Exception as ex:
        return float('inf'), float('inf')
import difflib
CAN = {'tdg': 't', 'sdg': 's'}
sig = [(CAN.get(op.name, op.name), tuple(qs)) for op, qs in data]
h = N // 2
first = sig[:h]; second = sig[h:][::-1]          # reversed second half: index i of `second` is gate N-1-i
sm = difflib.SequenceMatcher(None, first, second, autojunk=False)
pairs = []
for blk in sm.get_matching_blocks():
    for d in range(blk.size):
        j = blk.a + d; k = N - 1 - (blk.b + d)
        a, qa = data[j]; b, qb = data[k]
        if qa == qb and (a.name == b.name or INV.get(a.name) == b.name) and j != k:
            pairs.append((j, k))
shard, nsh = int(sys.argv[2]), int(sys.argv[3])
pairs = pairs[shard::nsh]
print(cid, 'N gates', N, 'mirror pairs (this shard)', len(pairs), flush=True)
rows = []; t0 = time.time()
for n_, (j, k) in enumerate(pairs):
    e, l = run(rebuild({j, k}))
    rows.append(dict(gates=[j, k], names=[data[j][0].name, data[k][0].name], qubits=data[j][1], err=e, leak=l, detected=bool(e > 1e-9 or l > 1e-9)))
    if n_ % 20 == 0: print(n_, len(pairs), 'elapsed %.0f' % (time.time() - t0), flush=True)
surv = [r for r in rows if not r['detected']]
print(cid, 'mirror-pair deletions', len(rows), 'detected', len(rows) - len(surv), 'survivors', len(surv), 'min err %.3e' % min(r['err'] for r in rows))
print('SURVIVORS', [(r['gates'], r['names'], r['qubits'], r['err']) for r in surv])
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), cid=cid, rows=rows, n_survivors=len(surv)), open(os.path.join(here, f'433-symdel-{cid}-{shard}.json'), 'w'), indent=1)
