"""Tester 441: LSH round 3, Aer statevector checks. (a) F5-003 and parent F1-002 and seed: 47-code check (outer untouched). (b) F3-003 (reads outer q13, q14 as controls): 12 seeded FULL 24-qubit states, pure/mixed in (bit13, bit14).
(a) all five + seed r00-seed-005 (no gate touches the outer register 'o'): Aer on data + ancilla qubits for the 47 inner codes, own target from the
    L13 rules (reuses tests/independent/lsh_m8_436/indep_check.py: own 47 inner codes, own K matrix), 3 angle pairs + 1 unused pair
    (1.13, 0.47); F4 touches nothing either (asserted by IC.outer_touched).
(b) removed in round 2: no program reads or writes an outer qubit (own_sparse.outer_roles is empty for all six).
Seed 20261119.   Run: PYTHONPATH=src taskset -c 0-1 tools/run-capped python results/tester/441/aer.py"""
import json, subprocess, sys, time, pathlib, gc
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.library import SetStatevector

ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "tests/independent/lsh_m8_436")); sys.path.insert(0, str(ROOT / "results/tester/441"))
import indep_check as IC
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL

SEED = 20261120
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": SEED, "inner47": {}, "F3_full": {}}
for eid in ("r03-F5-003", "r02-F1-002", "r00-seed-005"):
    f = ROOT / "compress/programs/lsh" / OS.PROGS[eid]
    r = {}
    for ab in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0), (1.13, 0.47)]:
        r[str(ab)] = IC.run_one(str(f), *ab, sign_check=(ab == (0.37, 0.61)))
    out["inner47"][eid] = r
    print(eid, {k: (v["op_norm_err"], v["anc_leak_prob"], v["gauss_leak_prob"]) for k, v in r.items()}, "wrong sign", r["(0.37, 0.61)"]["op_norm_err_vs_minus_beta"], flush=True)

rng = np.random.default_rng(SEED)
f = ROOT / "compress/programs/lsh" / OS.PROGS["r03-F3-003"]
b13 = np.array([(c >> 13) & 1 for c in OS.mine]); b14 = np.array([(c >> 14) & 1 for c in OS.mine])
combos = {(x, y): int(((b13 == x) & (b14 == y)).sum()) for x in (0, 1) for y in (0, 1)}
out["F3_full"]["n_states_by_bits_13_14"] = {str(k): v for k, v in combos.items()}
print("states per (bit13,bit14)", combos, flush=True)
kinds = [("pure", (x, y)) for (x, y) in combos if combos[(x, y)] > 0 for _ in range(2)] + [("mix", None)] * 4
states = []
for kind, xy in kinds:
    c = rng.normal(size=433) + 1j * rng.normal(size=433)
    if kind == "pure": c[~((b13 == xy[0]) & (b14 == xy[1]))] = 0
    states.append(c / np.linalg.norm(c))
sim = AerSimulator(method="statevector", max_parallel_threads=2)
res = {}
for (a, b) in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)]:
    qc = E.load_program(str(f)).build(LL.spec().with_angles(a, b)).circuit()
    assert qc.num_qubits == 24
    V = OS.target(a, b)
    errs = []; outer_changed = []; gauss = []; leak = []
    for (kind, xy), c in zip(kinds, states):
        psi = np.zeros(2 ** 24, complex); psi[OS.mine] = c
        circ = QuantumCircuit(24); circ.append(SetStatevector(psi), range(24)); circ.compose(qc, inplace=True); circ.save_statevector()
        tc = transpile(circ, sim, optimization_level=0); del circ
        rr = sim.run(tc).result(); sv = np.array(rr.get_statevector()); del rr, tc, psi; gc.collect()
        got = sv[OS.mine]; exp = V @ c
        ph = np.vdot(exp, got); ph /= abs(ph)
        errs.append(float(np.linalg.norm(got - ph * exp)))
        leak.append(float(1 - np.sum(np.abs(got) ** 2)))
        idx = np.flatnonzero(np.abs(sv) > 1e-13)
        def outer_hist(it):
            h = {}
            for k, v in it: h[k >> 12] = h.get(k >> 12, 0) + abs(v) ** 2
            return h
        hin = outer_hist((OS.mine[i], c[i]) for i in range(433)); hout = outer_hist((k, sv[k]) for k in idx)
        keys = set(hin) | set(hout)
        outer_changed.append(float(max(abs(hin.get(k, 0) - hout.get(k, 0)) for k in keys)))
        gauss.append(float(sum(abs(sv[k]) ** 2 for k in idx if OS.gauss_viol(k & 0xFFF))))
        del sv, idx; gc.collect()
        print("F3-003", (a, b), kind, xy, f"err {errs[-1]:.2e} leak {leak[-1]:.1e} outer-weight change {outer_changed[-1]:.1e} gauss {gauss[-1]:.1e}", flush=True)
    res[f"{a},{b}"] = {"kinds": [str(k) for k in kinds], "err": errs, "leak": leak, "outer_weight_change": outer_changed, "gauss_residual": gauss, "max_err": max(errs)}
out["F3_full"]["by_pair"] = res
json.dump(out, open(ROOT / "results/tester/441/aer.json", "w"), indent=1)
