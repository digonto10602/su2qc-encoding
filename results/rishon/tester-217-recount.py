"""Tester 217: independent recount of the cost key (CX, T at eps=1e-6, depth_CT, qubits) of the round-0 valid seeds.
Own code: lowering gate by gate with transpile(level 0) (Qiskit's own decompositions), CX / T counted from the gate list,
macro costs ALSO recomputed from a hand table of textbook decompositions, rz -> pygridsynth.gridsynth_gates (own call),
depth of the synthesised circuit.  No import of su2plaq.metrics."""
import sys, json, math, subprocess, importlib.util
import mpmath
from collections import Counter
from qiskit import QuantumCircuit, transpile
from pygridsynth.gridsynth import gridsynth_gates
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import evaluate as LE

BASIS = ['cx', 'h', 's', 'sdg', 't', 'tdg', 'x', 'z', 'rz']
# hand table (CX, T-count of the gate itself, number of rotation angles) of the textbook decompositions
HAND = {'cx': (1, 0, 0), 'cz': (1, 0, 0), 'ccx': (6, 7, 0), 'ccz': (6, 7, 0), 'rccx': (3, 4, 0), 'ch': (1, 2, 0), 'crx': (2, 0, 2),
        't': (0, 1, 0), 'tdg': (0, 1, 0), 'p': (0, 0, 1), 'rz': (0, 0, 1), 'x': (0, 0, 0), 'z': (0, 0, 0), 'h': (0, 0, 0), 's': (0, 0, 0), 'sdg': (0, 0, 0)}


def word(theta, eps):
    k = theta / (math.pi / 4)
    if abs(k - round(k)) < 1e-9:
        return ['', 'T', 'S', 'ST', 'SS', 'SST', 'SSS', 'SSST'][round(k) % 8]
    return str(gridsynth_gates(theta=mpmath.mpf(repr(theta)), epsilon=mpmath.mpf(repr(eps))))


def recount(qc, eps=1e-6):
    hand = Counter()
    for inst in qc.data:
        c = HAND[inst.operation.name]
        hand['cx'] += c[0]; hand['t'] += c[1]
    low = QuantumCircuit(qc.num_qubits)
    cache = {}
    for inst in qc.data:
        op = inst.operation
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if op.name in BASIS:
            low.append(op, qs); continue
        sub = QuantumCircuit(op.num_qubits); sub.append(op, list(range(op.num_qubits)))
        t = transpile(sub, basis_gates=BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
        for i in t.data:
            low.append(i.operation, [qs[t.find_bit(q).index] for q in i.qubits])
    ops = low.count_ops()
    cx = ops.get('cx', 0)
    t_gates = ops.get('t', 0) + ops.get('tdg', 0)
    out = QuantumCircuit(qc.num_qubits)
    t_rot = 0; n_rz = 0; n_rot = 0; t_fixed_rz = 0
    words = {}
    for inst in low.data:
        op = inst.operation; q = [low.find_bit(x).index for x in inst.qubits]
        if op.name != 'rz':
            out.append(op, q); continue
        th = float(op.params[0]); n_rz += 1
        w = words.get(th) or words.setdefault(th, word(th, eps))
        exact = abs(th / (math.pi / 4) - round(th / (math.pi / 4))) < 1e-9
        if exact: t_fixed_rz += w.count('T')
        else: n_rot += 1; t_rot += w.count('T')
        for ch in reversed(w):
            if ch == 'H': out.h(q[0])
            elif ch == 'S': out.s(q[0])
            elif ch == 'T': out.t(q[0])
            elif ch == 'X': out.h(q[0]); out.s(q[0]); out.s(q[0]); out.h(q[0])
            elif ch == 'W': pass
            else: raise ValueError(ch)
    t_fixed = t_gates + t_fixed_rz
    return dict(cx=cx, cx_hand=hand['cx'], t_gates=t_gates, t_hand=hand['t'], t_fixed=t_fixed, n_rot=n_rot, t_rot=t_rot, t_total=t_fixed + t_rot,
                depth_ct=out.depth(), qubits=qc.num_qubits, distinct_angles=len(words))


if __name__ == '__main__':
    s = rishon_spec('step')
    res = {}
    for label, path in (('general', 'compress/programs/rishon/seed/000-general.py'), ('general+polish', 'compress/programs/rishon/seed/010-general_polish.py')):
        qc = LE.load_program(path).build(s).circuit()
        res[label] = recount(qc)
        print(label, res[label], flush=True)
    json.dump({'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), 'eps': 1e-6, 'rows': res}, open('results/rishon/tester-217-recount.json', 'w'), indent=1)
