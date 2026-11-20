"""Tester 442: negative control for F3-004 (reads outer qubits q13, q14 as controls only): mutate the circuit on the outer-controlled cx gates and run
the own sparse engine on all 433 states at (0.37, 0.61); each mutation must FAIL (error O(1)).  No RNG."""
import json, sys, subprocess
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/results/tester/442")
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
f = "/home/digimonk/Projects/su2qc-encoding/compress/programs/lsh/F3/004-joint-sa-walk22.py"
qc = E.load_program(f).build(LL.spec()).circuit(); V = OS.target(0.37, 0.61)
g = OS.gates_of(qc); out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd="/home/digimonk/Projects/su2qc-encoding").stdout.strip(), "seed": None}
rep = lambda ctrls, new: [(a, [new if (a == "cx" and q[0] in ctrls) else q[0]] + q[1:], p) for a, q, p in g]
muts = {"original": g,
        "drop_cx_from_13": [x for x in g if not (x[0] == "cx" and x[1][0] == 13)],
        "drop_cx_from_14": [x for x in g if not (x[0] == "cx" and x[1][0] == 14)],
        "drop_cx_from_13_and_14": [x for x in g if not (x[0] == "cx" and x[1][0] in (13, 14))],
        "ctrl_13_replaced_by_q1": rep({13}, 1), "ctrl_14_replaced_by_q1": rep({14}, 1), "ctrl_13_14_replaced_by_q1": rep({13, 14}, 1)}
out["n_cx_from_13"] = sum(1 for x in g if x[0] == "cx" and x[1][0] == 13); out["n_cx_from_14"] = sum(1 for x in g if x[0] == "cx" and x[1][0] == 14)
out["errors"] = {}
for name, mut in muts.items():
    M, st = OS.block(mut); e, _ = OS.dist(M, V); out["errors"][name] = e; print(name, e, st)
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/442/f3_mutation.json", "w"), indent=1)
