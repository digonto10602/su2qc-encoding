"""Tester step 1.3 (diagnostic, no source change): synthesise U_B(0.61) from the PROGRAM-ORDER lowering (the simulator's own
per-gate decomposition) instead of metrics.cliffordt.lower() (Qiskit level-0 transpile, layer order); evaluate on the sparse engine.
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_synth_program_order.py out.json"""
import sys, json, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
from qiskit import QuantumCircuit
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_UB
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.metrics.logical import is_clifford_t_angle, logical_metrics
from su2plaq.metrics.cliffordt import pygridsynth_word, word_error

enc = TwelveQubit(); beta = 0.61; V = enc.target("UB", None, beta)
qc = build_UB(beta)
from qiskit import transpile
CT = ["cx", "h", "s", "sdg", "t", "tdg", "rz", "x", "z"]
cache = {}
def local_ct(op):
    key = (op.name, tuple(float(x) for x in op.params), op.num_qubits)
    if key not in cache:
        sub = QuantumCircuit(op.num_qubits); sub.append(op, list(range(op.num_qubits)))
        t = transpile(sub, basis_gates=CT, optimization_level=0, qubits_initially_zero=False, seed_transpiler=1)
        cache[key] = ([(i.operation.name, [t.find_bit(q).index for q in i.qubits], [float(x) for x in i.operation.params]) for i in t.data], float(t.global_phase))
    return cache[key]
res = {}
for eps in (1e-4, 1e-6):
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase); nrot = 0; tr = 0
    for inst in qc.data:
        qi = [qc.find_bit(q).index for q in inst.qubits]
        loc, gp = local_ct(inst.operation); out.global_phase += gp
        for name, lq, pl in loc:
            qs = [qi[k] for k in lq]
            if name == "rz" and not is_clifford_t_angle(pl[0]):
                nrot += 1; w = pygridsynth_word(pl[0], eps); tr += w.count("T")
                for ch in reversed(w):
                    if ch == "H": out.h(qs[0])
                    elif ch == "S": out.s(qs[0])
                    elif ch == "T": out.t(qs[0])
                    elif ch == "X": out.h(qs[0]), out.s(qs[0]), out.s(qs[0]), out.h(qs[0])
            elif name == "rz": out.rz(pl[0], qs[0])
            else: getattr(out, name)(*qs)
    tol = synth_tolerances(nrot, eps); t0 = time.time()
    v = evaluate(out, enc, V, engine="sparse", **tol)
    rec = dict(n_rot=nrot, t_rot=tr, ops_after=dict(out.count_ops()), tol=tol, ok=v.ok, reason=v.reason, engine=v.engine, certified=v.certified, op_norm=v.op_norm_error, block=v.block_error,
               leak_amp=v.leak_amplitude, gauss=v.gauss_residual, max_leak=v.max_leak, dirty=v.dirty_ancilla, seconds=v.seconds, wall=time.time() - t0)
    res[str(eps)] = rec; print(eps, rec, flush=True)
json.dump(res, open(sys.argv[1], "w"), indent=1, default=float)
