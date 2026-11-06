"""Tester 214: independent check that build_UB(beta, ladder in {ccx,rccx,mcx}) are the same unitary.
Own dict-based basis-state simulator (gate matrices from qiskit.quantum_info.Operator, not su2plaq.evaluate.sparse_sim).
Inputs: 48 seeded valid inner codes (seed 214) + 24 seeded arbitrary 16-bit codes (invalid ones included), ancillas |0>.
Outputs: max |amp_ladder - amp_ccx| over all output basis states, ancilla-return leakage, and ccx vs dense expm(-i beta H_B^in) on the valid codes.
Run: PYTHONPATH=src python results/rishon/tester-214-ladder-independent.py"""
import json, subprocess, time
import numpy as np, scipy.linalg as sla
from qiskit.quantum_info import Operator
from su2plaq.circuits import rishon as C
from su2plaq.rishon import operators as O

BETA, SEED = 0.61, 214
_cache = {}
def gate_matrix(op):
    key = (op.name, tuple(op.params))
    if key not in _cache: _cache[key] = np.asarray(Operator(op).data)
    return _cache[key]

def compile_circ(qc):
    return [(gate_matrix(i.operation), [qc.find_bit(q).index for q in i.qubits]) for i in qc.data]

def run(prog, code, tol=1e-14):
    st = {int(code): 1.0 + 0j}
    for M, qs in prog:
        new = {}
        for s, a in st.items():
            loc = sum(((s >> q) & 1) << k for k, q in enumerate(qs))
            base = s
            for q in qs: base &= ~(1 << q)
            col = M[:, loc]
            for r in np.flatnonzero(np.abs(col) > 1e-15):
                t = base
                for k, q in enumerate(qs): t |= ((r >> k) & 1) << q
                new[t] = new.get(t, 0) + a * col[r]
        st = {s: a for s, a in new.items() if abs(a) > tol}
    return st

rng = np.random.default_rng(SEED)
codes = O.inner_codes()
valid = rng.choice(codes, 48, replace=False)
arb = rng.integers(0, 1 << 16, 24)
progs = {l: compile_circ(C.build_UB(BETA, ladder=l)) for l in ("ccx", "rccx", "mcx")}
res = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip(), "beta": BETA, "seed": SEED,
       "n_valid": len(valid), "n_arbitrary": len(arb), "ladders": {}}
t0 = time.time()
outs = {l: {int(c): run(p, c) for c in np.concatenate([valid, arb])} for l, p in progs.items()}
for l in ("ccx", "rccx", "mcx"):
    leak = max(sum(abs(a) ** 2 for s, a in o.items() if s >> 16) for o in outs[l].values())
    d = {"max_ancilla_leak_prob": float(leak)}
    if l != "ccx":
        for name, sel in (("valid", valid), ("arbitrary", arb)):
            worst = 0.0
            for c in sel:
                a, b = outs["ccx"][int(c)], outs[l][int(c)]
                worst = max(worst, max(abs(a.get(s, 0) - b.get(s, 0)) for s in set(a) | set(b)))
            d[f"max_amp_diff_vs_ccx_{name}"] = float(worst)
    res["ladders"][l] = d
# anchor: ccx vs dense expm on valid codes
H = O.h_magnetic_inner(); U = sla.expm(-1j * BETA * (H.toarray() if hasattr(H, "toarray") else H))
idx = {int(c): i for i, c in enumerate(codes)}
for l in ("ccx", "rccx", "mcx"):
    worst = 0.0
    for c in valid:
        v = np.zeros(1296, complex)
        for s, a in outs[l][int(c)].items(): v[idx[s]] += a            # asserts output is a valid inner code
        worst = max(worst, np.abs(v - U[:, idx[int(c)]]).max())
    res["ladders"][l]["max_err_vs_dense_expm_valid"] = float(worst)
res["seconds"] = time.time() - t0
print(json.dumps(res, indent=1))
json.dump(res, open("results/rishon/tester-214-ladder-independent.json", "w"), indent=1)
