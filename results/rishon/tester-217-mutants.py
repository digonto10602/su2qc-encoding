"""Tester 217: sensitivity of my second engine: mutants of the general step circuit must be flagged."""
import importlib.util, json, numpy as np
spec_ = importlib.util.spec_from_file_location('eng', 'results/rishon/tester-217-engine.py'); eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE
from qiskit import QuantumCircuit
s = rishon_spec('step'); T = eng.algebra_targets(s.alpha, s.beta)
qc = LE.load_program('compress/programs/rishon/seed/000-general.py').build(s).circuit()
def run(qc2):
    ops = eng.lower(qc2); qs = eng.used_qubits(ops)
    sim = eng.Sim(T['codes'], qs); sim.run(ops)
    M, wd, wo = sim.block(T['codes'], list(range(16)))
    ph, e2, em = eng.compare(M, T['step'])
    return e2, float(np.sqrt(wd.max())), float(np.sqrt(wo.max()))
def mutate(kind, k):
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase); seen = 0; done = False
    for inst in qc.data:
        op = inst.operation; qs = list(inst.qubits)
        nm = op.name
        if kind == 'crx_angle_1e-6' and nm == 'crx':
            if seen == k and not done:
                op = op.__class__(float(op.params[0]) + 1e-6); done = True
            seen += 1
        elif kind == 'drop_cz' and nm == 'cz':
            if seen == k and not done: done = True; seen += 1; continue
            seen += 1
        elif kind == 'cx_target_swap' and nm == 'cx':
            if seen == k and not done: qs = qs[::-1]; done = True
            seen += 1
        elif kind == 'p_angle_1e-6' and nm == 'p':
            if seen == k and not done: op = op.__class__(float(op.params[0]) + 1e-6); done = True
            seen += 1
        out.append(op, qs)
    assert done
    return out
res = {'unmutated': run(qc)}
print('unmutated', res['unmutated'])
for kind, ks in (('crx_angle_1e-6', [0, 40, 80]), ('p_angle_1e-6', [0, 3]), ('drop_cz', [0, 100, 199]), ('cx_target_swap', [0, 500, 1000])):
    for k in ks:
        r = run(mutate(kind, k)); res[f'{kind}#{k}'] = r; print(kind, k, r, flush=True)
json.dump(res, open('results/rishon/tester-217-mutants.json', 'w'), indent=1)
