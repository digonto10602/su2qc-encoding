"""Tester 220 (adds the spectral norm of the leak operator X via scipy svds): independent Clifford+T re-verification: lower each round-1 program with transpile(level 0) to {cx,h,s,sdg,t,tdg,x,z,rz}, replace every rz by
my own pygridsynth word (eps = 1e-6), run MY sparse engine on all 1296 codes vs my dense target, compare with the budget N_rot*eps + 1e-9 (the production
budget is tol_err = N_rot*eps + ~1e-9).  usage: tester-221-synth.py [eps]"""
import sys, json, math, subprocess, importlib.util, os, time
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
R = imp("rc217", "tester-217-recount.py"); C = imp("c220", "tester-221-common.py"); eng = C.load_engine()
from qiskit import QuantumCircuit, transpile
from su2plaq.rishon.compress.spec import rishon_spec
eps = float(sys.argv[1]) if len(sys.argv) > 1 else 1e-6
s = rishon_spec('step')
T = eng.algebra_targets(s.alpha, s.beta)
res = {}
for cid, fam in C.CANDS:
    qc = C.build_circuit(cid, s)
    low = QuantumCircuit(qc.num_qubits)
    for inst in qc.data:
        op = inst.operation; qs = [qc.find_bit(q).index for q in inst.qubits]
        if op.name in R.BASIS:
            low.append(op, qs); continue
        sub = QuantumCircuit(op.num_qubits); sub.append(op, list(range(op.num_qubits)))
        t = transpile(sub, basis_gates=R.BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
        for i in t.data:
            low.append(i.operation, [qs[t.find_bit(q).index] for q in i.qubits])
    out = QuantumCircuit(qc.num_qubits)
    n_rot = 0; words = {}
    for inst in low.data:
        op = inst.operation; q = [low.find_bit(x).index for x in inst.qubits]
        if op.name != 'rz':
            out.append(op, q); continue
        th = float(op.params[0])
        w = words.get(th) or words.setdefault(th, R.word(th, eps))
        if abs(th / (math.pi / 4) - round(th / (math.pi / 4))) >= 1e-9: n_rot += 1
        for ch in reversed(w):
            if ch == 'H': out.h(q[0])
            elif ch == 'S': out.s(q[0])
            elif ch == 'T': out.t(q[0])
            elif ch == 'X': out.h(q[0]); out.s(q[0]); out.s(q[0]); out.h(q[0])
            elif ch == 'W': pass
            else: raise ValueError(ch)
    names = set(out.count_ops())
    ops = eng.lower(out); qs = eng.used_qubits(ops)
    t0 = time.time()
    sim = eng.Sim(T['codes'], qs, thr=1e-15); sim.run(ops)
    M, wd, wo = sim.block(T['codes'], list(range(16)))
    ph, e2, emax = eng.compare(M, T['step'])
    import scipy.sparse as sps, scipy.sparse.linalg as spl
    n = sim.n; st = sim.key & ((1 << n) - 1); col = sim.key >> n
    dmask = 0
    for q in range(16): dmask |= 1 << sim.pos[q]
    d = np.zeros(len(st), dtype=np.int64)
    for i in range(16): d |= ((st >> sim.pos[i]) & 1) << i
    lut = np.full(1 << 16, -1, dtype=np.int64); lut[np.asarray(T['codes'])] = np.arange(len(T['codes']))
    inc = ((st & ~np.int64(dmask)) == 0) & (lut[d] >= 0)
    ko = ~inc
    u, rowid = np.unique(st[ko], return_inverse=True)
    X = sps.csr_matrix((sim.amp[ko], (rowid, col[ko])), shape=(len(u), sim.ncol))
    sx = float(spl.svds(X, k=1, return_singular_vectors=False)[0]) if X.shape[0] > 1 else 0.0
    budget = n_rot * eps + 1e-9
    res[cid] = dict(n_rot=n_rot, eps=eps, budget=budget, block_err=e2, leak_spectral=sx, block_plus_leakspec=e2 + sx, leak=float(np.sqrt((wd + wo).max())), phase_abs=float(abs(ph)), gates=sorted(names),
                    cx=out.count_ops().get('cx', 0), t=out.count_ops().get('t', 0) + out.count_ops().get('tdg', 0), n_gates=len(out.data), max_state=int(sim.maxsize),
                    my_dropped_fro=float(np.sqrt(sim.dw_sq.sum())), ratio_to_budget=e2 / budget, seconds=time.time() - t0, outer_touched=sorted(q for q in qs if 16 <= q < 48))
    print(cid, res[cid], flush=True)
json.dump({'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), 'eps': eps, 'rows': res}, open(os.path.join(here, f'tester-221-synth-{eps:g}.json'), 'w'), indent=1)
