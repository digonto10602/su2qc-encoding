"""Tester 219: mutation sensitivity of MY sparse engine on the four round-1 circuits (seed 219): +1e-6 on a rotation angle (5 sites), delete a cx (3), t<->tdg (3),
cx control/target swapped (3).  Expectation: error >= 1e-7 (angle) / O(1) (others) vs unmutated ~2.5e-14."""
import sys, os, json, importlib.util, time, subprocess
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = imp("c220", "tester-221-common.py"); eng = C.load_engine()
from qiskit import QuantumCircuit
from su2plaq.rishon.compress.spec import rishon_spec
s = rishon_spec('step'); T = eng.algebra_targets(s.alpha, s.beta)
rng = np.random.default_rng(219)
def rebuild(qc, mut):
    out = QuantumCircuit(qc.num_qubits); out.global_phase = qc.global_phase
    for gi, inst in enumerate(qc.data):
        op = inst.operation; qs = [qc.find_bit(q).index for q in inst.qubits]
        m = mut.get(gi)
        if m is None: out.append(op, qs); continue
        kind = m[0]
        if kind == 'drop': continue
        if kind == 'angle':
            new = op.copy(); new.params = [op.params[0] + 1e-6]; out.append(new, qs)
        elif kind == 'tswap':
            getattr(out, 'tdg' if op.name == 't' else 't')(qs[0])
        elif kind == 'cxswap':
            out.cx(qs[1], qs[0])
    return out
def run(qc):
    ops = eng.lower(qc); qs = eng.used_qubits(ops)
    sim = eng.Sim(T['codes'], qs); sim.run(ops)
    M, wd, wo = sim.block(T['codes'], list(range(16)))
    ph, e2, _ = eng.compare(M, T['step'])
    return e2, float(np.sqrt((wd + wo).max()))
res = {}
for cid, fam in C.CANDS:
    qc = C.build_circuit(cid, s)
    names = [i.operation.name for i in qc.data]
    ang = [i for i, n in enumerate(names) if n in ('rz', 'p', 'cp', 'crx')]
    cxs = [i for i, n in enumerate(names) if n == 'cx']
    ts = [i for i, n in enumerate(names) if n in ('t', 'tdg')]
    rows = []
    base = run(qc); rows.append(('unmutated', -1, base))
    for kind, pool, k in (('angle', ang, 5), ('drop', cxs, 3), ('tswap', ts, 3), ('cxswap', cxs, 3)):
        for gi in sorted(rng.choice(pool, size=min(k, len(pool)), replace=False).tolist()):
            e, l = run(rebuild(qc, {gi: (kind,)}))
            rows.append((kind, gi, (e, l)))
    res[cid] = [dict(kind=k, gate=g, err=e[0], leak=e[1]) for k, g, e in rows]
    print(cid, 'unmutated %.1e' % base[0], '| min err by kind:', {k: '%.1e' % min(r['err'] for r in res[cid] if r['kind'] == k) for k in ('angle', 'drop', 'tswap', 'cxswap')}, flush=True)
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), seed=219, rows=res), open(os.path.join(here, 'tester-221-mutants.json'), 'w'), indent=1)
