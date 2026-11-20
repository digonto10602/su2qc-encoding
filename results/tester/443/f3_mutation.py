"""Tester 443: negative controls for the three round-5 programs (all read outer qubits q13, q14 as cx controls): delete / re-route the outer-controlled cx
gates, own sparse engine, all 433 states at (0.37, 0.61); each mutation must FAIL (error O(1)).  Also reports every outer-qubit role (cx control count).  No RNG."""
import json, sys, subprocess
ROOT = "/home/digimonk/Projects/su2qc-encoding"
sys.path.insert(0, ROOT + "/results/tester/443")
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None, "programs": {}}
V = OS.target(0.37, 0.61)
for eid in ("r05-F3-005", "r05-F5-005", "r05-F1-004"):
    f = f"{ROOT}/compress/programs/lsh/" + OS.PROGS[eid]
    qc = E.load_program(f).build(LL.spec()).circuit()
    g = OS.gates_of(qc)
    outer_ctrls = sorted({x[1][0] for x in g if x[0] == "cx" and x[1][0] >= 12})
    rep = lambda ctrls, new: [(a, [new if (a == "cx" and q[0] in ctrls) else q[0]] + q[1:], p) for a, q, p in g]
    muts = {"original": g}
    for q in outer_ctrls:
        muts[f"drop_cx_from_{q}"] = [x for x in g if not (x[0] == "cx" and x[1][0] == q)]
        muts[f"ctrl_{q}_replaced_by_q1"] = rep({q}, 1)
    muts["drop_all_outer"] = [x for x in g if not (x[0] == "cx" and x[1][0] in outer_ctrls)]
    muts["ctrl_all_outer_replaced_by_q1"] = rep(set(outer_ctrls), 1)
    r = {"outer_controls": outer_ctrls, "n_cx_from": {int(q): sum(1 for x in g if x[0] == "cx" and x[1][0] == q) for q in outer_ctrls}, "errors": {}}
    for name, mut in muts.items():
        M, st = OS.block(mut); e, _ = OS.dist(M, V); r["errors"][name] = e; print(eid, name, round(e, 6), st, flush=True)
    out["programs"][eid] = r
json.dump(out, open(ROOT + "/results/tester/443/f3_mutation.json", "w"), indent=1)
