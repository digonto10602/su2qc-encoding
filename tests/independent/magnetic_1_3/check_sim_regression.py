"""Tester step 1.3: simulator regression after the translation-path change (program order + cached per-gate decomposition).
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_sim_regression.py results/m1_step_1_3_sim_regression.json
"""
import sys, json, time, subprocess
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Gate
from qiskit.circuit.library import (MCXGate, C3XGate, C4XGate, C3SXGate, RCCXGate, RC3XGate, MCXVChain, MCXGrayCode, RZGate, RYGate,
                                   RXGate, PhaseGate, UGate, HGate, XGate)
from qiskit.quantum_info import Operator, random_unitary
from qiskit_aer import AerSimulator
import su2plaq.evaluate.sparse_sim as ss

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted",
       "seeds": "circuits 3000..3035 (default_rng), prune 80 seeds 0..79"}
sim = AerSimulator(method="statevector")

def dense_of(b, ncol):
    d = np.zeros((2 ** b.n_qubits, ncol), complex); np.add.at(d, (b.keys, b.cols), b.amps); return d

IN = ["h","sx","u","rz","p","cp","ccx","ccz","swap","unitary","cx","cz","t","tdg","s","sdg","x","z"]
FOREIGN = ["ry","rx","y","sxdg","cy","ch","crz","crx","cry","cswap","rzz","rxx","iswap","u3","rccx","rc3x","c3sx","mcp3","cu","custom","custom_nested","ecr","dcx","csx","cu3","mcrz"]
_CNT = 0
def add(qc, g, qs, a, rng):
    if g in ("h","sx","t","tdg","s","sdg","x","z","y","sxdg"): getattr(qc, g)(qs[0])
    elif g == "u": qc.u(a, float(rng.uniform(-3,3)), float(rng.uniform(-3,3)), qs[0])
    elif g == "u3": qc.u(a, 0.3, -1.1, qs[0])
    elif g in ("rz","p","ry","rx"): getattr(qc, g)(a, qs[0])
    elif g in ("cp","crz","crx","cry","rzz","rxx"): getattr(qc, g)(a, qs[0], qs[1])
    elif g == "cu3": qc.append(__import__("qiskit.circuit.library", fromlist=["CU3Gate"]).CU3Gate(a, .2, .5), qs[:2])
    elif g == "cu": qc.cu(a, .4, -.7, .9, qs[0], qs[1])
    elif g in ("cx","cz","swap","cy","ch","iswap","ecr","dcx","csx"): getattr(qc, g)(qs[0], qs[1])
    elif g in ("ccx","ccz","cswap"): getattr(qc, g)(*qs[:3])
    elif g == "rccx": qc.append(RCCXGate(), qs[:3])
    elif g == "rc3x": qc.append(RC3XGate(), qs[:4])
    elif g == "c3sx": qc.append(C3SXGate(), qs[:4])
    elif g == "mcp3": qc.mcp(a, qs[:3], qs[3])
    elif g == "mcrz": qc.append(RZGate(a).control(3), qs[:4])
    elif g == "unitary":
        q2 = sorted(qs[:2], reverse=bool(rng.integers(2))); qc.append(random_unitary(4, seed=int(rng.integers(1 << 30))), q2)
    elif g == "custom":
        s = QuantumCircuit(3, name="macroA"); s.h(0); s.cx(0, 1); s.rccx(1, 2, 0) if False else s.ccx(0, 1, 2); s.t(2); s.sx(1)
        qc.append(s.to_gate(), qs[:3])
    elif g == "custom_nested":
        s = QuantumCircuit(3); s.rx(0.3, 0); s.append(RCCXGate(), [0, 1, 2]); s.cry(0.8, 2, 1)
        t = QuantumCircuit(4); t.append(s.to_gate(), [0, 1, 2]); t.append(s.to_gate(), [3, 2, 1]); t.ch(0, 3)
        qc.append(t.to_gate(), qs[:4])
    elif g in ("custom_param", "custom_param_unique"):
        global _CNT
        _CNT += 1
        s = QuantumCircuit(2, name="pg" if g == "custom_param" else f"pg{_CNT}"); s.ry(a, 0); s.cx(0, 1); s.rz(2 * a, 1)
        qc.append(s.to_gate(), qs[:2])

def rand_circ(n, ng, rng, pool):
    qc = QuantumCircuit(n, global_phase=float(rng.uniform(-3, 3)))
    for _ in range(ng):
        g = pool[int(rng.integers(len(pool)))]
        qs = [int(q) for q in rng.choice(n, size=4, replace=False)]
        add(qc, g, qs, float(rng.uniform(-3, 3)), rng)
        if rng.random() < 0.05: qc.barrier()
    return qc

# ---------------- (a) 36 random circuits vs Aer SV and dense Operator, program order and DAG path -------------------
rows = []
for seed in range(36):
    rng = np.random.default_rng(3000 + seed)
    n = int(rng.integers(5, 12)); ng = int(rng.integers(30, 80))
    pool = IN + (FOREIGN if seed % 3 != 2 else [])
    qc = rand_circ(n, ng, rng, pool)
    qc.append(random_unitary(4, seed=seed), [0, n - 1])
    inputs = np.array(sorted(set(rng.integers(0, 2 ** n, size=min(2 ** n, 24)).tolist())), dtype=np.int64)
    b = ss.run_batch(qc, inputs)                        # program order first
    ops, ph = ss._translate(qc)
    bp = ss._run(ops, ph, n, inputs, 10 ** 8, range(len(ops)))
    bd = ss._run(ops, ph, n, inputs, 10 ** 8, ss._schedule(ops))
    D, Dp, Dd = dense_of(b, len(inputs)), dense_of(bp, len(inputs)), dense_of(bd, len(inputs))
    U = Operator(qc).data
    e_op = float(np.abs(U[:, inputs] - D).max())
    e_po_dag = float(np.abs(Dp - Dd).max())
    e_aer = 0.0
    for c in range(len(inputs)):
        prep = QuantumCircuit(n)
        for bt in range(n):
            if (int(inputs[c]) >> bt) & 1: prep.x(bt)
        prep.compose(qc, inplace=True); prep.save_statevector()
        sv = np.asarray(sim.run(transpile(prep, sim, optimization_level=0)).result().get_statevector())
        e_aer = max(e_aer, float(np.abs(sv - D[:, c]).max()))
    gnames = sorted({i.operation.name for i in qc.data})
    rows.append(dict(seed=3000 + seed, n=n, gates=len(qc.data), foreign=int(any(g not in ss.SIM_BASIS and g != "barrier" for g in gnames)),
                     err_op=e_op, err_aer=e_aer, prog_vs_dag=e_po_dag, norm_dev=float(np.abs(np.linalg.norm(D, axis=0) - 1).max()),
                     dropped=b.dropped_max))
    print(rows[-1], flush=True)
out["random"] = rows
out["random_summary"] = {k: max(r[k] for r in rows) for k in ("err_op", "err_aer", "prog_vs_dag", "norm_dev", "dropped")}
out["random_summary"]["n_circuits"] = len(rows); out["random_summary"]["n_with_foreign"] = sum(r["foreign"] for r in rows)
print(out["random_summary"])

# ---------------- (b) hostile translation cases -----------------------------------------------------------------------
host = {}
def full_err(qc):
    n = qc.num_qubits; b = ss.run_batch(qc, np.arange(2 ** n, dtype=np.int64)); return float(np.abs(dense_of(b, 2 ** n) - Operator(qc).data).max())
# same name, no params, different content: cache collision?
q = QuantumCircuit(3)
for variant in range(3):
    s = QuantumCircuit(2, name="macro")
    [lambda: s.cx(0, 1), lambda: s.cz(0, 1), lambda: (s.h(0), s.cx(1, 0))][variant]()
    q.append(s.to_gate(), [0, 1] if variant != 1 else [1, 2])
q.h(0)
host["same_name_different_content"] = full_err(q)
# same name, same params, different ctrl_state
q = QuantumCircuit(4); q.h([0, 1, 2])
q.append(RZGate(0.4).control(3, ctrl_state=7), [0, 1, 2, 3]); q.append(RZGate(0.4).control(3, ctrl_state=2), [0, 1, 2, 3]); q.append(RZGate(0.4).control(3, ctrl_state=5), [0, 1, 2, 3])
q.append(RYGate(0.4).control(2, ctrl_state=1), [0, 1, 3]); q.append(RYGate(0.4).control(2, ctrl_state=2), [0, 1, 3])
q.cx(0, 3, ctrl_state=0); q.ccx(0, 1, 3, ctrl_state=1); q.ch(0, 3, ctrl_state=0)
host["ctrl_state_variants"] = full_err(q)
# same gate twice with different qubits (cache holds local qubit indices)
q = QuantumCircuit(5); q.h(range(5))
for a, b_, c in ((0, 1, 2), (4, 2, 0), (3, 1, 4)): q.append(RCCXGate(), [a, b_, c]); q.append(RC3XGate(), [a, b_, c, (c + 1) % 5 if (c + 1) % 5 not in (a, b_, c) else (c + 2) % 5])
host["same_gate_different_qubits"] = full_err(q)
# float params nearly equal (cache key by exact float)
q = QuantumCircuit(3); q.h(0); q.append(RZGate(0.3).control(2), [0, 1, 2]); q.append(RZGate(0.3 + 1e-9).control(2), [0, 1, 2]); q.crx(0.3, 0, 1); q.crx(0.3 + 1e-12, 0, 1)
host["close_params"] = full_err(q)
# global phase on top of foreign gates, and gates whose decomposition carries a phase
q = QuantumCircuit(3, global_phase=0.77); q.h(0); q.append(UGate(0.4, 0.2, 0.9).control(1), [0, 1]); q.cu(0.5, 0.1, 0.2, 0.3, 1, 2); q.sx(0); q.sxdg(2); q.iswap(0, 2)
host["global_phase_mix"] = full_err(q)
# parametrised: bound Parameter
from qiskit.circuit import Parameter
th = Parameter("t"); q = QuantumCircuit(2); q.h(0); q.crx(th, 0, 1); q = q.assign_parameters({th: 0.81}); host["bound_parameter"] = full_err(q)
rngh = np.random.default_rng(5)
for g_ in ("custom_param", "custom_param_unique"):
    q = QuantumCircuit(4); q.h([0,1,2,3])
    for a_ in (0.7, -1.3, 0.2): add(q, g_, [0, 1, 2, 3], a_, rngh); add(q, g_, [3, 2, 0, 1], a_ + .5, rngh)
    host["same_name_param_gates" if g_ == "custom_param" else "unique_name_param_gates"] = full_err(q)
# empty circuit and barrier-only; one-qubit circuit; foreign gate at the edge of 62 qubits
q = QuantumCircuit(3); q.barrier(); host["barrier_only"] = full_err(q)
print(host)
out["hostile"] = host

# rejections
rej = {}
def tryrej(name, f, n=6):
    qc = QuantumCircuit(n, n); qc.h(0)
    try:
        f(qc); ss.run_batch(qc, np.array([0], dtype=np.int64)); rej[name] = "NOT rejected"
    except ValueError as e: rej[name] = "ValueError"
    except Exception as e: rej[name] = "other:" + type(e).__name__
tests_rej = {
 "qc.mcx(3)": lambda q: q.mcx([0,1,2],3), "qc.mcx(4)": lambda q: q.mcx([0,1,2,3],4), "qc.mcx(5)": lambda q: q.mcx([0,1,2,3,4],5),
 "C3XGate": lambda q: q.append(C3XGate(),[0,1,2,3]), "C4XGate": lambda q: q.append(C4XGate(),[0,1,2,3,4]),
 "MCXGate(3)": lambda q: q.append(MCXGate(3),[0,1,2,3]), "mcx recursion": lambda q: q.mcx([0,1,2,3],4,mode="recursion"),
 "mcx v-chain": lambda q: q.mcx([0,1,2],3,[4,5],mode="v-chain"), "MCXVChain": lambda q: q.append(MCXVChain(3),[0,1,2,3,4]),
 "MCXGrayCode": lambda q: q.append(MCXGrayCode(3),[0,1,2,3]),
 "XGate().control(3)": lambda q: q.append(XGate().control(3),[0,1,2,3]),
 "mcx ctrl_state": lambda q: q.mcx([0,1,2],3,ctrl_state=2),
 "mcx3 + unitary": lambda q: (q.append(random_unitary(4,seed=1),[0,1]), q.mcx([0,1,2],3)),
}
def wrapped(depth, kind):
    def f(q):
        sub = QuantumCircuit(5); sub.mcx([0,1,2],3) if kind == "mcx" else sub.append(C4XGate(), [0,1,2,3,4])
        for _ in range(depth):
            outer = QuantumCircuit(5); outer.append(sub.to_gate(), range(5)); sub = outer
        q.append(sub.to_gate(), [0,1,2,3,4])
    return f
for d in (1, 2, 3): tests_rej[f"wrapped mcx3 depth {d}"] = wrapped(d, "mcx")
tests_rej["wrapped c4x depth 1"] = wrapped(1, "c4x")
tests_rej["wrapped in to_instruction"] = lambda q: q.append((lambda s: (s.mcx([0,1,2],3), s.to_instruction())[1])(QuantumCircuit(4)), [0,1,2,3])
tests_rej["named wrapper with mcx"] = lambda q: q.append((lambda s: (s.mcx([0,1,2],3), s.to_gate())[1])(QuantumCircuit(4, name="my_h")), [0,1,2,3])
tests_rej["measure"] = lambda q: q.measure(0, 0)
tests_rej["reset"] = lambda q: q.reset(1)
tests_rej["delay"] = lambda q: q.delay(10, 1)
def _ift(q):
    with q.if_test((q.clbits[0], 1)): q.x(1)
tests_rej["if_test (control flow)"] = _ift
def _forl(q):
    with q.for_loop(range(2)): q.x(1)
tests_rej["for_loop"] = _forl
for k, f in tests_rej.items(): tryrej(k, f)
print(rej)
out["rejections"] = rej
# controls: must not be rejected
ok = {}
for name, f in {"ccx": lambda q: q.ccx(0,1,2), "mcx2": lambda q: q.mcx([0,1],2), "mcp4": lambda q: q.mcp(.7,[0,1,2,3],4), "rccx": lambda q: q.append(RCCXGate(),[0,1,2]),
                "rc3x": lambda q: q.append(RC3XGate(),[0,1,2,3]), "c3sx": lambda q: q.append(C3SXGate(),[0,1,2,3]),
                "ccx via ancilla": lambda q: (q.ccx(0,1,4), q.ccx(4,2,3), q.ccx(0,1,4)),
                "wrapped rccx": lambda q: q.append((lambda s:(s.append(RCCXGate(),[0,1,2]), s.to_gate())[1])(QuantumCircuit(3)),[0,1,2])}.items():
    qc = QuantumCircuit(6); qc.h(0); qc.h(4); f(qc); ok[name] = full_err(qc)
print(ok); out["accepted_exact"] = ok

# ---------------- (c) cap behaviour and path equality -----------------------------------------------------------------
cap = {}
k = 10
qc = QuantumCircuit(k + 1)
for q_ in range(k): qc.h(q_)
for q_ in range(k): qc.h(q_)       # program order opens 2^k, DAG order closes each H pair immediately
qc.t(0)
inp = np.array([0], dtype=np.int64)
ops, ph = ss._translate(qc)
for name, order in (("program", range(len(ops))), ("dag", ss._schedule(ops))):
    try:
        b = ss._run(ops, ph, k + 1, inp, 200, order); cap[f"{name}_cap200"] = f"ok stored={len(b.keys)}"
    except ss.SimCapExceeded: cap[f"{name}_cap200"] = "SimCapExceeded"
b = ss.run_batch(qc, inp, cap=200)
cap["run_batch_cap200_fallback"] = f"ok stored={len(b.keys)} amp0={b.amps[0]:.6f}"
cap["run_batch_equals_dense"] = float(np.abs(dense_of(b, 1)[:, 0] - Operator(qc).data[:, 0]).max()) if k + 1 <= 11 else None
try:
    b50 = ss.run_batch(qc, inp, cap=50); cap["run_batch_cap50"] = f"no exception (DAG order peak <=4 stored, stored={len(b50.keys)})"
except ss.SimCapExceeded: cap["run_batch_cap50"] = "SimCapExceeded (both orders over cap)"
# circuit exceeding the cap in both orders (genuinely wide)
q2 = QuantumCircuit(14)
for i in range(14): q2.h(i); q2.rz(0.3 + .1 * i, i)
try:
    ss.run_batch(q2, inp, cap=1000); cap["wide_cap1000"] = "NO exception"
except ss.SimCapExceeded: cap["wide_cap1000"] = "SimCapExceeded"
print(cap); out["cap"] = cap

# ---------------- (d) forced-pruning certified bound (80 circuits x 6 thresholds x columns) ---------------------------
def run_thr(qc, inputs, thr):
    old = ss.PRUNE_REL; ss.PRUNE_REL = thr
    try: return ss.run_batch(qc, np.asarray(inputs, dtype=np.int64), cap=50_000_000)
    finally: ss.PRUNE_REL = old
def percol_err(b1, b0, ncol):
    d = dense_of(b1, ncol) - dense_of(b0, ncol); return np.sqrt((np.abs(d) ** 2).sum(axis=0))
def rcirc(n, ng, rng, tiny):
    qc = QuantumCircuit(n, global_phase=float(rng.uniform(-3, 3)))
    for _ in range(ng):
        g = rng.choice(["h","sx","u","ry","rz","cx","ccx","cp","unitary","swap","t","crx","rccx","custom_param_unique"], p=[.18,.04,.12,.08,.08,.1,.05,.05,.04,.04,.08,.04,.05,.05])
        qs = [int(x) for x in rng.choice(n, size=3, replace=False)]
        ang = float(rng.choice([1e-1, 1e-3, 1e-6]) * rng.uniform(-1, 1)) if tiny else float(rng.uniform(-3, 3))
        if g == "u": qc.u(ang, float(rng.uniform(-3,3)), float(rng.uniform(-3,3)), qs[0])
        elif g in ("ry","rz"): getattr(qc, g)(ang, qs[0])
        elif g in ("h","sx","t"): getattr(qc, g)(qs[0])
        elif g in ("cx","swap"): getattr(qc, g)(qs[0], qs[1])
        elif g == "ccx": qc.ccx(*qs)
        elif g == "cp": qc.cp(ang, qs[0], qs[1])
        elif g == "crx": qc.crx(ang, qs[0], qs[1])
        elif g == "rccx": qc.append(RCCXGate(), qs)
        elif g == "custom_param_unique": add(qc, g, qs, ang, rng)
        else: qc.append(random_unitary(4, seed=int(rng.integers(1 << 30))), qs[:2])
    return qc
viol = 0; ncase = 0; worst_ex = -1.0; worst_ratio = 0.0
for seed in range(80):
    rng = np.random.default_rng(seed); n = int(rng.integers(5, 9)); qc = rcirc(n, int(rng.integers(30, 90)), rng, tiny=bool(seed % 2))
    inputs = np.arange(2 ** n)
    b0 = run_thr(qc, inputs, 0.0)
    if seed < 20: assert np.abs(dense_of(b0, len(inputs)) - Operator(qc).data).max() < 1e-12
    for thr in (1e-1, 1e-2, 1e-3, 1e-5, 1e-8, 1e-14):
        b1 = run_thr(qc, inputs, thr); e = percol_err(b1, b0, len(inputs)); bd = b1.dropped_l2
        ex = float((e - bd).max()); worst_ex = max(worst_ex, ex); ncase += len(inputs)
        if (bd > 1e-12).any(): worst_ratio = max(worst_ratio, float((e / np.maximum(bd, 1e-300))[bd > 1e-12].max()))
        if ex > 1e-13: viol += 1; print("VIOLATION", seed, thr, ex)
out["prune"] = dict(cases=ncase, violations=viol, worst_err_minus_bound=worst_ex, max_err_over_bound=worst_ratio)
print(out["prune"])
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
