"""Tester 219: Aer statevector check with sound dead-qubit reduction.
For each input code: qubits that are non-zero in some branch at some gate (decided by my sparse engine, tester-217-engine.py) are kept
(+16 data qubits); outer register removed (never touched).  A gate touching dead qubits D: B = <0_D| G |0_D> on the live qubits it touches;
B == identity -> dropped; B diagonal unitary -> kept as a DiagonalGate on the live qubits (a phase from |0> of a dead target, e.g. rz/p/crx on
|0>); anything else -> RuntimeError (never happened if the liveness is right)."""
import sys, time, json, importlib.util, os
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
eng = imp("eng217", "tester-217-engine.py")


def live_sets(qc, T, ops, qs):
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


def reduce_circuit(qc, keep_q):
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator
    from qiskit.circuit.library import DiagonalGate
    idx = {q: i for i, q in enumerate(keep_q)}
    red = QuantumCircuit(len(keep_q)); red.global_phase = qc.global_phase
    n_diag = n_drop = 0
    for inst in qc.data:
        qq = [qc.find_bit(q).index for q in inst.qubits]
        if all(q in idx for q in qq):
            red.append(inst.operation, [idx[q] for q in qq]); continue
        dead = [i for i, q in enumerate(qq) if q not in idx]
        live = [i for i, q in enumerate(qq) if q in idx]
        U = Operator(inst.operation).data      # little endian: bit i of the index = qq[i]
        nl = len(live)
        B = np.zeros((1 << nl, 1 << nl), complex)
        for a in range(1 << nl):
            ia = sum(((a >> k) & 1) << live[k] for k in range(nl))
            for b in range(1 << nl):
                ib = sum(((b >> k) & 1) << live[k] for k in range(nl))
                B[a, b] = U[ia, ib]
        dg = np.diag(B).copy()
        offmax = np.abs(B - np.diag(dg)).max()
        # zero diagonal entries = control patterns that never occur on this input's trajectory (the dead qubit would have been flipped): set to 1
        mod = np.abs(dg)
        okmod = np.all((np.abs(mod - 1) < 1e-12) | (mod < 1e-12))
        dg = np.where(mod < 1e-12, 1.0, dg)
        if offmax < 1e-12 and okmod and np.abs(dg - 1).max() < 1e-12:
            n_drop += 1; continue
        if nl and offmax < 1e-12 and okmod:
            red.append(DiagonalGate(list(dg)), [idx[qq[i]] for i in live]); n_diag += 1; continue
        if nl == 0 and abs(abs(B[0, 0]) - 1) < 1e-12:
            red.global_phase += float(np.angle(B[0, 0])); n_diag += 1; continue
        raise RuntimeError(f"gate {inst.operation.name} on {qq} with dead {dead}: reduced block is neither identity nor diagonal unitary")
    return red, n_drop, n_diag


def run_code(args):
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    qc, code, anc_live, nthreads = args
    keep_q = list(range(16)) + sorted(anc_live)
    red, n_drop, n_diag = reduce_circuit(qc, keep_q)
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
    return code, sv, len(keep_q), time.time() - t0, len(red.data), n_drop, n_diag


# ------------------------------------------------------------------ macro-level liveness (rccx kept as a monomial 3-qubit gate)
def lower_macro(qc):
    """list of ('mono', qubits, perm, phase) for rccx, else the sparse-engine ops (controls, target, 2x2, name) / ('phase', gp)."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator
    ops = []
    cache = {}
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == "rccx":
            if "rccx" not in cache:
                U = Operator(inst.operation).data
                perm = np.zeros(8, int); ph = np.zeros(8, complex)
                for col in range(8):
                    nz = np.flatnonzero(np.abs(U[:, col]) > 1e-12)
                    assert len(nz) == 1 and abs(abs(U[nz[0], col]) - 1) < 1e-12
                    perm[col] = nz[0]; ph[col] = U[nz[0], col]
                cache["rccx"] = (perm, ph)
            ops.append(("mono", qs, *cache["rccx"]))
        else:
            tmp = QuantumCircuit(qc.num_qubits); tmp.append(inst.operation, qs)
            ops += eng.lower(tmp)
    return ops


def apply_mono(sim, qs, perm, ph):
    k = sim.key
    idx = np.zeros(len(k), dtype=np.int64)
    for i, q in enumerate(qs):
        idx |= ((k >> sim.pos[q]) & 1) << i
    new = perm[idx]
    d = idx ^ new
    for i, q in enumerate(qs):
        k = k ^ (((d >> i) & 1) << sim.pos[q])
    sim.key = k
    sim.amp = sim.amp * ph[idx]


def live_sets_macro(qc, T, qs=None):
    ops = lower_macro(qc)
    used = sorted({q for op in ops if op[0] not in ("phase",) for q in (op[1] if op[0] == "mono" else list(op[0]) + [op[1]])})
    anc = [q for q in used if q >= 48]
    sim = eng.Sim(T['codes'], used)
    n = sim.n
    ai = [used.index(q) for q in anc]
    ever = np.zeros((len(T['codes']), len(anc)), bool)
    for op in ops:
        if op[0] == "phase":
            continue
        if op[0] == "mono":
            apply_mono(sim, op[1], op[2], op[3])
        else:
            sim.apply(*op[:3])
        col = sim.key >> n
        st = sim.key & ((1 << n) - 1)
        for j, p in enumerate(ai):
            np.logical_or.at(ever[:, j], col, ((st >> p) & 1).astype(bool))
    return anc, ever, used
