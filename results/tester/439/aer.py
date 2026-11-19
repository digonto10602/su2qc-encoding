"""Tester 439: LSH round 2, Aer statevector checks.
(a) all five + seed r00-seed-005 (no gate touches the outer register 'o'): Aer on data + ancilla qubits for the 47 inner codes, own target from the
    L13 rules (reuses tests/independent/lsh_m8_436/indep_check.py: own 47 inner codes, own K matrix), 3 angle pairs + 1 unused pair
    (1.13, 0.47); F4 touches nothing either (asserted by IC.outer_touched).
(b) removed in round 2: no program reads or writes an outer qubit (own_sparse.outer_roles is empty for all six).
Seed 20261119.   Run: PYTHONPATH=src taskset -c 0-1 tools/run-capped python results/tester/439/aer.py"""
import json, subprocess, sys, time, pathlib, gc
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.library import SetStatevector

ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "tests/independent/lsh_m8_436")); sys.path.insert(0, str(ROOT / "results/tester/439"))
import indep_check as IC
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL

SEED = 20261119
PROGS = OS.PROGS
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": SEED, "inner47": {}}
for eid in ("r02-F1-002", "r02-F2-002", "r02-F3-002", "r02-F4-002", "r02-F5-002", "r00-seed-005"):
    f = ROOT / "compress/programs/lsh" / PROGS[eid]
    r = {}
    for ab in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0), (1.13, 0.47)]:
        r[str(ab)] = IC.run_one(str(f), *ab, sign_check=(ab == (0.37, 0.61)))
    out["inner47"][eid] = r
    print(eid, {k: (v["op_norm_err"], v["anc_leak_prob"], v["gauss_leak_prob"]) for k, v in r.items()}, "wrong sign", r["(0.37, 0.61)"]["op_norm_err_vs_minus_beta"], flush=True)

json.dump(out, open(ROOT / "results/tester/439/aer.json", "w"), indent=1)
