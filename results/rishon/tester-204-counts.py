"""Tester 204: gate counts of build_UB / build_step vs Qiskit count_ops, my own CX/T accounting, and a real transpile."""
import sys, json, subprocess
sys.path.insert(0, 'src')
from collections import Counter
import numpy as np
import su2plaq.circuits.rishon as C
from qiskit import transpile
out = {'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip() + '+uncommitted'}
lm = __import__('su2plaq.metrics.logical', fromlist=['x']).logical_metrics
COST = {  # (cx, t_fixed, n_rot) from METHODS.md macro table
 'cx': (1, 0, 0), 'cz': (1, 0, 0), 'ccx': (6, 7, 0), 'ccz': (6, 7, 0), 'ch': (1, 2, 0), 'crx': (2, 0, 2), 'crz': (2, 0, 2), 'cp': (2, 0, 3),
 'rccx': (3, 4, 0), 'swap': (3, 0, 0), 'x': (0, 0, 0), 'z': (0, 0, 0), 'h': (0, 0, 0), 's': (0, 0, 0), 'p': (0, 0, 1), 'rz': (0, 0, 1)}
for name, qc in [('UB', C.build_UB(0.61)), ('step1', C.build_step(0.37, 0.61, 1)), ('step2', C.build_step(0.37, 0.61, 2))]:
    ops = qc.count_ops()
    cx = sum(COST[k][0] * v for k, v in ops.items()); t = sum(COST[k][1] * v for k, v in ops.items()); nrot = sum(COST[k][2] * v for k, v in ops.items())
    m = lm(qc)
    # real transpile to Clifford+T+rz
    tq = transpile(qc, basis_gates=['cx', 'h', 't', 'tdg', 's', 'sdg', 'x', 'y', 'z', 'rz'], optimization_level=0)
    tops = tq.count_ops()
    import math
    nonc = 0
    for inst in tq.data:
        if inst.operation.name == 'rz':
            a = float(inst.operation.params[0]) / (math.pi / 4)
            if abs(a - round(a)) > 1e-9: nonc += 1
    # classify rz multiples of pi/4 as T-type
    trz = sum(1 for inst in tq.data if inst.operation.name == 'rz' and abs((float(inst.operation.params[0]) / (math.pi / 4)) - round(float(inst.operation.params[0]) / (math.pi / 4))) < 1e-9 and round(float(inst.operation.params[0]) / (math.pi / 4)) % 2 != 0)
    out[name] = {'count_ops': dict(ops), 'qubits': qc.num_qubits, 'depth': qc.depth(), 'my_cx': cx, 'my_t_fixed': t, 'my_n_rot': nrot,
                 'prod_logical_metrics': {k: m[k] for k in ('cx', 't_fixed', 'n_rot', 'qubits', 'depth') if k in m},
                 'transpiled_cx': int(tops.get('cx', 0)), 'transpiled_t': int(tops.get('t', 0) + tops.get('tdg', 0) + trz), 'transpiled_nonclifford_rz': nonc,
                 'native_mcx_ge3': int(sum(1 for i in qc.data if i.operation.name.startswith('mcx') or (i.operation.name in ('ccx', 'ccz') and len(i.qubits) > 3))),
                 'n_gates': len(qc.data), 'names': sorted(ops)}
    print(name, json.dumps(out[name])[:900])
# layout: ancillas, no outer
q = C.build_UB(0.61, with_outer=True)
used = {q.find_bit(b).index for i in q.data for b in i.qubits}
out['UB_with_outer'] = {'qubits': q.num_qubits, 'registers': [(r.name, r.size) for r in q.qregs], 'outer_qubits_touched': sorted(x for x in used if 16 <= x < 48), 'metadata_keys': sorted(q.metadata)}
q0 = C.build_UB(0.61)
out['UB_registers'] = [(r.name, r.size) for r in q0.qregs]
# pair_frames sanity
fr = C.pair_frames(0.61)
out['pair_frames'] = {'n': len(fr), 'kappa': dict(Counter(round(f['kappa'], 9) for f in fr)), 'angle_over_beta_abs': dict(Counter(round(abs(f['angle_over_beta']), 9) for f in fr)),
                      'n_controls_hist': dict(Counter(len(f['controls']) for f in fr)), 'keys': sorted(fr[0])}
# frame gate vocabulary
voc = Counter(n for f in fr for n, _ in f['frame_gates'])
out['frame_gate_vocab'] = dict(voc)
json.dump(out, open('results/rishon/tester-204-counts.json', 'w'), indent=1, default=str)
