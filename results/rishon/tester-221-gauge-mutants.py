"""Tester 220: exhaustive single-gate mutant battery on the round-3 programs, my sparse engine (tester-217-engine.py), all 1296 codes, nominal pair (0.37, 0.61).
For every gate of the program's (macro-level) circuit:
  drop       delete the gate (every gate of every type except none excluded; 'gauge' = s, sdg, t, tdg, z, cz, ccz)
  tswap      t <-> tdg;  sswap  s <-> sdg
  rccx2ccx   replace a relative-phase Toffoli by the exact Toffoli
  cxswap     cx control/target swapped (a random 12 per program, seed 220)
  angle      rz/p parameter + 1e-6;  flip: parameter sign flipped
Detected = block error > 1e-9 or leak > 1e-9 or the engine raises.  Unmutated baseline ~ 2e-14.
usage: tester-221-gauge-mutants.py <cid>"""
import sys, os, json, importlib.util, time, subprocess
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = imp("c220", "tester-221-common.py"); eng = C.load_engine()
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate
from su2plaq.rishon.compress.spec import rishon_spec
cid = sys.argv[1]
s = rishon_spec('step'); T = eng.algebra_targets(s.alpha, s.beta)
rng = np.random.default_rng(220)
qc = C.build_circuit(cid, s)
data = [(i.operation, [qc.find_bit(q).index for q in i.qubits]) for i in qc.data]
def rebuild(gi, kind):
    out = QuantumCircuit(qc.num_qubits); out.global_phase = qc.global_phase
    for j, (op, qs) in enumerate(data):
        if j != gi:
            out.append(op, qs); continue
        if kind == 'drop': continue
        if kind == 'angle':
            new = op.copy(); new.params = [op.params[0] + 1e-6]; out.append(new, qs)
        elif kind == 'flip':
            new = op.copy(); new.params = [-op.params[0]]; out.append(new, qs)
        elif kind == 'tswap': getattr(out, 'tdg' if op.name == 't' else 't')(qs[0])
        elif kind == 'sswap': getattr(out, 'sdg' if op.name == 's' else 's')(qs[0])
        elif kind == 'rccx2ccx': out.ccx(*qs)
        elif kind == 'cxswap': out.cx(qs[1], qs[0])
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
names = [op.name for op, qs in data]
muts = []
for gi, n in enumerate(names):
    muts.append((gi, 'drop'))
    if n in ('t', 'tdg'): muts.append((gi, 'tswap'))
    if n in ('s', 'sdg'): muts.append((gi, 'sswap'))
    if n == 'rccx': muts.append((gi, 'rccx2ccx'))
    if n in ('rz', 'p'): muts += [(gi, 'angle'), (gi, 'flip')]
cxs = [i for i, n in enumerate(names) if n == 'cx']
for gi in sorted(rng.choice(cxs, size=12, replace=False).tolist()): muts.append((gi, 'cxswap'))
t0 = time.time()
base = run(qc)
print(cid, 'baseline', base, 'n mutants', len(muts), flush=True)
rows = []
for k, (gi, kind) in enumerate(muts):
    e, l = run(rebuild(gi, kind))
    rows.append(dict(gate=gi, name=names[gi], qubits=data[gi][1], kind=kind, err=e, leak=l, detected=bool(e > 1e-9 or l > 1e-9)))
    if k % 50 == 0: print(k, len(muts), 'elapsed %.0f' % (time.time() - t0), flush=True)
surv = [r for r in rows if not r['detected']]
summ = {}
for r in rows:
    d = summ.setdefault(r['kind'] + ':' + r['name'], [0, 0, 1e300]); d[0] += 1; d[1] += r['detected']; d[2] = min(d[2], r['err'])
print(cid, 'total', len(rows), 'detected', len(rows) - len(surv), 'survivors', len(surv), 'seconds %.0f' % (time.time() - t0))
for k, v in sorted(summ.items()): print('  %-14s n=%3d detected=%3d min_err=%.2e' % (k, v[0], v[1], v[2]))
print('SURVIVORS', [(r['gate'], r['kind'], r['name'], r['qubits'], r['err']) for r in surv])
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), cid=cid, seed=220, baseline=base, pair=[s.alpha, s.beta], rows=rows, summary=summ), open(os.path.join(here, f'tester-221-gauge-mutants-{cid}.json'), 'w'), indent=1)
