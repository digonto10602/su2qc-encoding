"""Tester 438: negative control for F3: delete the six cx gates whose control is the outer qubit 13 (resp. replace the control by data qubit 1) -> must fail on the 433 states."""
import json, sys, pathlib
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/results/tester/438")
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
f = "/home/digimonk/Projects/su2qc-encoding/compress/programs/lsh/F3/001-pfold-3and-ungated-mux.py"
qc = E.load_program(f).build(LL.spec()).circuit(); V = OS.target(0.37, 0.61)
g = OS.gates_of(qc); out = {}
for name, mut in (("original", g), ("drop_cx_from_13", [x for x in g if not (x[0] == "cx" and x[1][0] == 13)]),
                  ("cx_13_replaced_by_q1", [(a, [1 if (a == "cx" and q[0] == 13) else q[0]] + q[1:], p) for a, q, p in g])):
    M, st = OS.block(mut); e, _ = OS.dist(M, V); out[name] = e; print(name, e, st)
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/438/f3_mutation.json", "w"), indent=1)
