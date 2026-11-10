"""Tester 3.L3 soundness probes of su2plaq_cert_spinnet: wrong-but-plausible circuits built by the tester (not the builder's
tampering tests).  Every probe goes through lean_export.certify (exporter + Lean checker)."""
import json, sys, pathlib, time, math, tempfile
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import ZGate, XGate, CCXGate
from su2plaq.circuits.spinnet import build_step, build_UB, build_UE
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet import lean_export as LE

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
CERTS = OUT / 'certs'
enc = SpinNet()
A, B = 0.37, 0.61
res = []
def record(name, claim, r, expect):
    ok = (r['status'] in expect)
    res.append(dict(probe=name, claim=claim, status=r['status'], reason=r['reason'][:160], expect=list(expect), ok=ok,
                    check_s=r.get('check_seconds')))
    print(('OK  ' if ok else 'BAD ') + f"{name:48s} {r['status']:9s} {r['reason'][:110]}", flush=True)
def cert(qc, kind='step', order=1, a=A, b=B):
    return LE.certify(qc, enc, kind, a, b, order, out_dir=CERTS)
def rebuild(qc, edit):
    """edit(idx, inst) -> list of (op, qargs) replacing instruction idx"""
    new = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase)
    for idx, inst in enumerate(qc.data):
        for op, qa in edit(idx, inst):
            new.append(op, qa)
    return new
def q(qc, qb): return qc.find_bit(qb).index

base = build_step(A, B, 1, with_outer=True)
record('baseline step o1', 'step o1', cert(base), {'certified'})
print([ (i, inst.operation.name, [q(base,x) for x in inst.qubits]) for i, inst in enumerate(base.data)])

# 1. rz sign flips (each of 4) and all four together (beta -> -beta)
rz_idx = [i for i, inst in enumerate(base.data) if inst.operation.name == 'rz']
for i in rz_idx:
    def ed(idx, inst, i=i):
        if idx == i:
            op = inst.operation.copy(); op.params = [-float(op.params[0])]
            return [(op, inst.qubits)]
        return [(inst.operation, inst.qubits)]
    record(f'rz sign flip at gate {i}', 'step o1', cert(rebuild(base, ed)), {'rejected', 'n_a'})
def ed_all(idx, inst):
    if inst.operation.name == 'rz':
        op = inst.operation.copy(); op.params = [-float(op.params[0])]; return [(op, inst.qubits)]
    return [(inst.operation, inst.qubits)]
record('all 4 rz flipped (beta -> -beta)', 'step o1', cert(rebuild(base, ed_all)), {'rejected', 'n_a'})
def ed_p(idx, inst):
    if inst.operation.name == 'p':
        op = inst.operation.copy(); op.params = [-float(op.params[0])]; return [(op, inst.qubits)]
    return [(inst.operation, inst.qubits)]
record('all 4 p (U_E) flipped (alpha -> -alpha)', 'step o1', cert(rebuild(base, ed_p)), {'rejected', 'n_a'})
# rz angle rescaled by an exact rational (still linear in beta): factor 2 on one rotation
for i in rz_idx[:2]:
    def ed(idx, inst, i=i):
        if idx == i:
            op = inst.operation.copy(); op.params = [2 * float(op.params[0])]; return [(op, inst.qubits)]
        return [(inst.operation, inst.qubits)]
    record(f'rz x2 (still linear) gate {i}', 'step o1', cert(rebuild(base, ed)), {'rejected', 'n_a'})
# tiny perturbation 1e-10 relative (below the exporter's 1e-12? no: above) and 1e-14
for eps in (1e-10, 1e-13):
    def ed(idx, inst, eps=eps):
        if idx == rz_idx[0]:
            op = inst.operation.copy(); op.params = [float(op.params[0]) * (1 + eps)]; return [(op, inst.qubits)]
        return [(inst.operation, inst.qubits)]
    record(f'rz perturbed rel {eps:g}', 'step o1', cert(rebuild(base, ed)), {'rejected', 'n_a', 'certified'})

# 2. every CX reversed
cx_idx = [i for i, inst in enumerate(base.data) if inst.operation.name == 'cx']
for i in cx_idx:
    def ed(idx, inst, i=i):
        if idx == i: return [(inst.operation, inst.qubits[::-1])]
        return [(inst.operation, inst.qubits)]
    record(f'cx reversed at gate {i}', 'step o1', cert(rebuild(base, ed)), {'rejected', 'n_a'})

# 3. delete every single instruction (all gates incl. corner-qubit gates)
for i, inst in enumerate(base.data):
    def ed(idx, ins, i=i):
        return [] if idx == i else [(ins.operation, ins.qubits)]
    nm = inst.operation.name; qs = [q(base, x) for x in inst.qubits]
    record(f'drop gate {i} {nm}{qs}', 'step o1', cert(rebuild(base, ed)), {'rejected', 'n_a'})

# 4. global phase / ancilla phase
b2 = base.copy(); b2.global_phase = base.global_phase + 0.3
record('global_phase += 0.3 (circuit property)', 'step o1', cert(b2), {'certified'})   # absorbed in c by design
anc0 = base.qregs[2][0]
b3 = base.copy(); b3.rz(0.3, anc0)
record('rz(0.3) on clean ancilla (non-linear phase)', 'step o1', cert(b3), {'n_a', 'rejected'})
b4 = base.copy(); b4.rz(B / 2, anc0)
record('rz(beta/2) on clean ancilla (linear phase)', 'step o1', cert(b4), {'certified', 'rejected'})
b5 = base.copy(); b5.p(0.3, base.qregs[0][1])
record('p(0.3) on data qubit 1 (relative phase)', 'step o1', cert(b5), {'n_a', 'rejected'})
b6 = base.copy(); b6.p(B, base.qregs[0][1])
record('p(beta) on data qubit 1 (relative phase, linear)', 'step o1', cert(b6), {'rejected'})
b7 = base.copy(); b7.x(anc0)
record('X on clean ancilla at end (dirty ancilla)', 'step o1', cert(b7), {'rejected'})
b8 = base.copy(); b8.h(base.qregs[0][0])
record('extra H on data qubit 0 (leak)', 'step o1', cert(b8), {'rejected'})

# 5. order / kind confusions
o1 = base; o2 = build_step(A, B, 2, with_outer=True)
record('order-1 circuit claimed order 2', 'step o2', cert(o1, 'step', 2), {'rejected', 'n_a'})
record('order-2 circuit claimed order 1', 'step o1', cert(o2, 'step', 1), {'rejected', 'n_a'})
record('order-2 circuit claimed order 2 (control)', 'step o2', cert(o2, 'step', 2), {'certified'})
ub = build_UB(B, with_outer=True); ue = build_UE(A, with_outer=True)
record('UB circuit control', 'UB', cert(ub, 'UB'), {'certified'})
record('UE circuit control', 'UE', cert(ue, 'UE'), {'certified'})
record('UB circuit claimed step', 'step o1', cert(ub, 'step'), {'rejected', 'n_a'})
record('UE circuit claimed step', 'step o1', cert(ue, 'step'), {'rejected', 'n_a'})
record('step circuit claimed UB', 'UB', cert(base, 'UB'), {'rejected', 'n_a'})
record('step circuit claimed UE', 'UE', cert(base, 'UE'), {'rejected', 'n_a'})
record('UB circuit claimed UE', 'UE', cert(ub, 'UE'), {'rejected', 'n_a'})
# claimed angles wrong
record('step(0.37,0.61) claimed (0.74,0.61)', 'step o1', cert(base, 'step', 1, 0.74, 0.61), {'rejected', 'n_a'})
record('step(0.37,0.61) claimed (0.37,1.22)', 'step o1', cert(base, 'step', 1, 0.37, 1.22), {'rejected', 'n_a'})
record('step(0.37,0.61) claimed (0.61,0.37)', 'step o1', cert(base, 'step', 1, 0.61, 0.37), {'rejected', 'n_a'})
# circuit with swapped roles: U_E angle used for beta
record('step(0.61,0.37) claimed (0.37,0.61)', 'step o1', cert(build_step(B, A, 1, with_outer=True)), {'rejected', 'n_a'})
# product order reversed: U_E then U_B vs U_B then U_E
def order_swapped():
    u = build_UB(B, with_outer=True); e = build_UE(A, with_outer=True)
    c = QuantumCircuit(*u.qregs); c.compose(u, inplace=True); c.compose(e, inplace=True); return c
record('UB.UE composed vs step target (order of product)', 'step o1', cert(order_swapped()), {'certified', 'rejected'})
def order_swapped2():
    u = build_UB(B, with_outer=True); e = build_UE(A, with_outer=True)
    c = QuantumCircuit(*u.qregs); c.compose(e, inplace=True); c.compose(u, inplace=True); return c
record('UE then UB composed (the other order) claimed step', 'step o1', cert(order_swapped2()), {'certified', 'rejected'})

# 6. single-state sensitivity: sign flip on exactly one of the 433 states (k = 0, 216, 432) via a multi-controlled Z built
#    from clean ancillas; the checker must say "state k differs".
codes = [int(c[0]) for c in enc.physical_vectors().codes]
def one_state_flip(k, where='end'):
    code = codes[k]
    d, o, a = base.qregs
    a2 = QuantumRegister(16, 'a')
    c = QuantumCircuit(d, o, a2, global_phase=base.global_phase)
    c.compose(base.copy().decompose(reps=0) if False else base, qubits=list(d) + list(o) + list(a2)[:7], inplace=True)
    ctrl = list(d) + list(o)
    zeros = [ctrl[i] for i in range(16) if not (code >> i) & 1]
    def gadget():
        for z in zeros: c.x(z)
        c.ccx(ctrl[0], ctrl[1], a2[7])
        for i in range(2, 16):
            c.ccx(ctrl[i], a2[7 + i - 2], a2[7 + i - 1])   # a2[7..15]: 9 ancillas -> needs up to a2[7+14]=a2[21]; guarded below
        for z in zeros: c.x(z)
    return None
# AND of 16 controls needs 14 ancillas: use 15 ancillas total beyond the original 7 -> build explicitly
def one_state_flip2(k):
    code = codes[k]
    d, o, a = base.qregs
    a2 = QuantumRegister(7 + 15, 'a')
    c = QuantumCircuit(d, o, a2, global_phase=base.global_phase)
    c.compose(base, qubits=list(d) + list(o) + list(a2)[:7], inplace=True)
    ctrl = list(d) + list(o)
    zeros = [ctrl[i] for i in range(16) if not (code >> i) & 1]
    ex = list(a2)[7:]
    for z in zeros: c.x(z)
    c.ccx(ctrl[0], ctrl[1], ex[0])
    for i in range(2, 16): c.ccx(ctrl[i], ex[i - 2], ex[i - 1])
    c.z(ex[14])
    for i in range(15, 1, -1): c.ccx(ctrl[i], ex[i - 2], ex[i - 1])
    c.ccx(ctrl[0], ctrl[1], ex[0])
    for z in zeros: c.x(z)
    return c
for k in (0, 1, 216, 431, 432):
    r = cert(one_state_flip2(k))
    record(f'sign flip on exactly state k={k} (code {codes[k]})', 'step o1', r, {'rejected'})
    res[-1]['reason_expected_k'] = (f'state {k} ' in r['reason'] + ' ')
    print('      mentions state', k, ':', res[-1]['reason_expected_k'])
json.dump(res, open(OUT / 'probes.json', 'w'), indent=1)
print('SUMMARY', sum(r['ok'] for r in res), '/', len(res), 'as expected')
