"""Tester 217: counts (CX, T_fixed, N_rot, lowered depth) of the three rejected seeds and the whole-circuit L3 row, own recount."""
import sys, json, math, importlib.util, subprocess
spec_ = importlib.util.spec_from_file_location('rc', 'results/rishon/tester-217-recount.py'); rc = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(rc)
from qiskit import QuantumCircuit, transpile
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress import baselines as BL
from su2plaq.compress import evaluate as LE
s = rishon_spec('step')

def lowered(qc):
    low = QuantumCircuit(qc.num_qubits)
    for inst in qc.data:
        op = inst.operation; qs = [qc.find_bit(q).index for q in inst.qubits]
        if op.name in rc.BASIS: low.append(op, qs); continue
        sub = QuantumCircuit(op.num_qubits); sub.append(op, list(range(op.num_qubits)))
        t = transpile(sub, basis_gates=rc.BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
        for i in t.data: low.append(i.operation, [qs[t.find_bit(q).index] for q in i.qubits])
    return low

def counts(qc):
    low = lowered(qc); ops = low.count_ops()
    t_fixed = ops.get('t', 0) + ops.get('tdg', 0); n_rot = 0
    for inst in low.data:
        if inst.operation.name == 'rz':
            th = float(inst.operation.params[0]); k = th / (math.pi / 4)
            if abs(k - round(k)) < 1e-9:
                t_fixed += round(k) % 2
            else: n_rot += 1
    return dict(cx=ops.get('cx', 0), t_fixed=t_fixed, n_rot=n_rot, depth_lowered=low.depth(), est_t_eps_1e6=t_fixed + n_rot * 3 * math.log2(1e6))

P = 'compress/programs/rishon/seed/'
rows = {}
for lab, path in (('general', '000-general.py'), ('general-rccx', '001-general-rccx.py'), ('general-mcx', '002-general-mcx.py')):
    rows[lab] = counts(LE.load_program(P + path).build(s).circuit()); print(lab, rows[lab], flush=True)
rows['qiskit_l3'] = counts(BL.qiskit_l3(s, seed=12345)); print('qiskit_l3', rows['qiskit_l3'], flush=True)
rows['qiskit_l3_whole'] = counts(BL.qiskit_l3_whole(s)); print('qiskit_l3_whole', rows['qiskit_l3_whole'], flush=True)
json.dump({'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), 'rows': rows}, open('results/rishon/tester-217-recount2.json', 'w'), indent=1)
