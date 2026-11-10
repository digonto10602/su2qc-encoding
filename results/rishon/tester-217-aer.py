"""Tester 217: Aer statevector check of the 16 data + live ancilla qubits (outer register removed: the circuit never touches it).
For each input code c: the circuit is restricted to the qubits that are non-zero in some branch of c's trajectory (decided by tester-217-engine.py),
gates touching a never-non-zero ancilla are dropped (identity per the sparse engine), the code is loaded with X gates, Aer 'statevector'
(double precision, 1 thread) returns the output; the amplitudes on <code'| with clean ancillas are column c of M_aer."""
import sys, time, json, importlib.util, os
import numpy as np
spec_ = importlib.util.spec_from_file_location('eng', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tester-217-engine.py'))
eng = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(eng)


def live_sets(qc, T, ops, qs):
    """per column: boolean array over used ancillas: ever non-zero (any branch)."""
    anc = [q for q in qs if q >= 48]
    ai = [qs.index(q) for q in anc]
    sim = eng.Sim(T['codes'], qs)
    n = sim.n
    ever = np.zeros((len(T['codes']), len(anc)), bool)
    for op in ops:
        if op[0] == 'phase':
            continue
        sim.apply(*op[:3])
        col = sim.key >> n
        st = sim.key & ((1 << n) - 1)
        for j, p in enumerate(ai):
            np.logical_or.at(ever[:, j], col, ((st >> p) & 1).astype(bool))
    return anc, ever


def run_code(args):
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    qc, code, anc_live, nthreads = args
    keep_q = list(range(16)) + sorted(anc_live)
    idx = {q: i for i, q in enumerate(keep_q)}
    red = QuantumCircuit(len(keep_q))
    red.global_phase = qc.global_phase
    for inst in qc.data:
        qq = [qc.find_bit(q).index for q in inst.qubits]
        if all(q in idx for q in qq):
            red.append(inst.operation, [idx[q] for q in qq])
        # else: touches a never-non-zero ancilla -> identity on this input's trajectory (sparse engine)
    pre = QuantumCircuit(len(keep_q))
    for b in range(16):
        if (code >> b) & 1:
            pre.x(b)
    full = pre.compose(red)
    full.save_statevector()
    sim = AerSimulator(method='statevector', precision='double', max_parallel_threads=nthreads, fusion_enable=True)
    t0 = time.time()
    tq = transpile(full, sim, optimization_level=0)
    res = sim.run(tq).result()
    sv = np.asarray(res.get_statevector(), dtype=complex)
    return code, sv, len(keep_q), time.time() - t0, len(red.data)
