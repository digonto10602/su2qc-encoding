"""Tester 215 probe (a)+(b): own mutants of the general UE and step circuits through su2plaq.rishon.compress.evaluate.
Usage: python tester-215-mutants.py UE|step  -> results/rishon/tester-215-mutants-<kind>.json   (seed 215)"""
import json, sys, time, subprocess
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import CircuitInstruction
import su2plaq.rishon.compress as RC
from su2plaq.rishon.compress import spec as S, baselines as BL, evaluate as EV

kind = sys.argv[1]
spec = S.rishon_spec(kind)
qc0 = BL.general_circuit(spec)
rng = np.random.default_rng(215)
out = []
def setp(qc, i, params, qubits=None):
    q = qc.copy(); inst = q.data[i]
    op = inst.operation.copy(); op.params = params
    q.data[i] = CircuitInstruction(op, inst.qubits if qubits is None else qubits, inst.clbits); return q
def run(label, qc, expect, modes=("full",), **kw):
    for mode in modes:
        t = time.time(); r = EV.evaluate_circuit(qc, spec, mode=mode, **kw)
        v = r.verdict
        row = dict(label=label, mode=mode, valid=r.valid, reason=r.reason, expect_valid=expect[0], expect_reason=expect[1],
                   err=None if v is None else v.op_norm_error, leak=None if v is None else v.max_leak,
                   dropped=None if v is None else v.dropped_total, outer_read=None if v is None else v.outer_bits_read,
                   wall=time.time() - t, ok=(r.valid == expect[0]) and (expect[1] is None or r.reason.startswith(expect[1])))
        print(row, flush=True); out.append(row)
ops = [(i, x.operation.name) for i, x in enumerate(qc0.data)]
names = lambda n: [i for i, o in ops if o == n]
modes = ("trial", "full")
run("baseline", qc0, (True, "ok"), modes)
# 1. crx / (UE: p) angle * (1 + 1e-6)
rot = "crx" if kind == "step" else "p"
for i in names(rot)[:1] + names(rot)[-1:]:
    p = float(qc0.data[i].operation.params[0])
    run(f"{rot}[{i}] angle x(1+1e-6)", setp(qc0, i, [p * (1 + 1e-6)]), (False, "error"), modes)
if kind == "step":
    ix = names("crx"); i = ix[len(ix)//2]; p = float(qc0.data[i].operation.params[0])
    run(f"crx[{i}] angle x(1+1e-6)", setp(qc0, i, [p * (1 + 1e-6)]), (False, "error"), modes)
# 2. ccx control swapped (replace one control with a different data qubit)
    cc = names("ccx"); picks = [cc[0], cc[len(cc)//3], cc[2*len(cc)//3], cc[-1]]
    for i in picks:
        qs = list(qc0.data[i].qubits); idx = [qc0.find_bit(q).index for q in qs]
        others = [j for j in range(16) if j not in idx]
        new = int(rng.choice(others)); qs2 = [qc0.qubits[new]] + qs[1:]
        q = qc0.copy(); inst = q.data[i]; q.data[i] = CircuitInstruction(inst.operation, qs2, inst.clbits)
        run(f"ccx[{i}] {idx} control0 -> {new}", q, (False, "error"), modes)
# 3. X on an outer qubit then undone (adjacent, and across the circuit)
q = qc0.copy(); q.x(20); q.x(20)
run("x(20);x(20) at end (outer touch)", q, (False, "writes_outer"), modes)
q = QuantumCircuit(*qc0.qregs); q.x(17); q.compose(qc0, qubits=list(range(qc0.num_qubits)), inplace=True); q.x(17)
run("x(17) before and after (outer touch)", q, (False, "writes_outer"), modes)
q = qc0.copy(); q.h(30); q.h(30)
run("h(30);h(30) (outer touch)", q, (False, "writes_outer"), modes)
# 4. ancilla left dirty
q = qc0.copy(); a = QuantumRegister(1, "dirty"); q.add_register(a); q.x(a[0])
run("extra ancilla flipped (x)", q, (False, None), modes)
q = qc0.copy(); a = QuantumRegister(1, "dirty2"); q.add_register(a); q.cx(0, a[0])
run("extra ancilla cx(0,a)", q, (False, None), modes)
if kind == "step":
    q = qc0.copy(); anc = q.num_qubits - 1; q.x(anc)
    run("existing last ancilla left at |1>", q, (False, None), modes)
# 5. global phase only gates
q = qc0.copy(); q.x(0); q.z(0); q.x(0); q.z(0)
run("x z x z on qubit 0 (= -1)", q, (True, "ok"), modes)
q = qc0.copy(); q.rz(0.7, 3); q.p(-0.7, 3)
run("rz(0.7) p(-0.7) on qubit 3 (= e^{-0.35i})", q, (True, "ok"), modes)
q = qc0.copy(); q.global_phase += 1.1
run("qc.global_phase += 1.1", q, (True, "ok"), modes)
json.dump(dict(kind=kind, commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), seed=215, rows=out), open(f"results/rishon/tester-215-mutants-{kind}.json", "w"), indent=1, default=float)
print("ALL AS EXPECTED:", all(r["ok"] for r in out))
