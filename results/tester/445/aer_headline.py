"""Tester 445 (adapted from 444 aer.py): LSH M8 headline r05-F3-005.  Tester 444: LSH round 6, Aer statevector checks.  the round-6 program (F3-006) reads the outer qubits q13, q14 as cx controls, so the
47-inner-code Aer check is NOT sufficient: each is run on the same 12 seeded FULL 24-qubit states (2 pure in each (bit13, bit14) sector + 4 mixed), 3 angle pairs,
own target (expm of 6j block, own 24-bit codes); outputs checked for error, leak out of the 433 codes, change of the outer-register weight, Abelian Gauss weight.
Seed 20261121.   Run: PYTHONPATH=src taskset -c 0-1 tools/run-capped python results/tester/444/aer.py"""
import json, subprocess, sys, time, pathlib, gc
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.library import SetStatevector

ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "tests/independent/lsh_m8_436")); sys.path.insert(0, str(ROOT / "results/tester/444"))
import indep_check as IC
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL

SEED = 20261121
OUTJSON = "results/tester/445/aer_headline.json"
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": SEED, "full": {}}
rng = np.random.default_rng(SEED)
b13 = np.array([(c >> 13) & 1 for c in OS.mine]); b14 = np.array([(c >> 14) & 1 for c in OS.mine])
combos = {(x, y): int(((b13 == x) & (b14 == y)).sum()) for x in (0, 1) for y in (0, 1)}
out["n_states_by_bits_13_14"] = {str(k): v for k, v in combos.items()}
print("states per (bit13,bit14)", combos, flush=True)
kinds = [("pure", (x, y)) for (x, y) in combos if combos[(x, y)] > 0 for _ in range(2)] + [("mix", None)] * 4
states = []
for kind, xy in kinds:
    c = rng.normal(size=433) + 1j * rng.normal(size=433)
    if kind == "pure": c[~((b13 == xy[0]) & (b14 == xy[1]))] = 0
    states.append(c / np.linalg.norm(c))
sim = AerSimulator(method="statevector", max_parallel_threads=2)
out["full"] = {}
for eid in ("r05-F3-005",):
    f = ROOT / "compress/programs/lsh" / OS.PROGS[eid]
    res = {}
    for (a, b) in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)]:
        if (a, b) == (0.37, 0.61):
            from qiskit import qpy
            qc = qpy.load(open(ROOT / 'results/lsh/m8-headline-step.qpy', 'rb'))[0]
        else:
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
        print(eid, (a, b), f"max err {max(errs):.2e} max leak {max(leak):.1e} max outer-weight change {max(outer_changed):.1e} max gauss {max(gauss):.1e}", flush=True)
        res[f"{a},{b}"] = {"kinds": [str(k) for k in kinds], "err": errs, "leak": leak, "outer_weight_change": outer_changed, "gauss_residual": gauss, "max_err": max(errs)}
    out["full"][eid] = res
json.dump(out, open(ROOT / OUTJSON, "w"), indent=1)
