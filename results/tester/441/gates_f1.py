"""Tester 441: structural claims of round 3.
(A) F5-003 vs its parent F1-002: native gate lists differ by exactly the ladder cx(9,3) -> cx(0,3)?  (positions, counts)
(B) F3-003 vs F3-001: gate counts, native frame (46 CX, 24 fixed T) -- CX of the F3-003 circuit split into "frame" vs "walk".
(C) F3-003 qubit roles: which qubits are read (q13, q14) and what are they (site 0's l_2v, l_v1: own bit layout 12 + 3c + {0,1,2} = (l_pn, l_nv, l_vp) of outer site c).
No RNG.   Run: PYTHONPATH=src python results/tester/441/gates_f1.py -> results/tester/441/gates_f1.json"""
import json, sys, subprocess, pathlib, warnings
warnings.filterwarnings("ignore")
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/441"))
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
P = lambda rel: ROOT / "compress/programs/lsh" / rel
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
def g(eid, a=0.37, b=0.61): return OS.gates_of(E.load_program(str(P(OS.PROGS[eid]))).build(LL.spec().with_angles(a, b)).circuit())
out["A"] = {}
for (a, b) in OS.PAIRS:
    G5, G1 = g("r03-F5-003", a, b), g("r02-F1-002", a, b)
    diff = [(i, x[:2], y[:2]) for i, (x, y) in enumerate(zip(G5, G1)) if x != y]
    out["A"][f"{a},{b}"] = {"len": [len(G5), len(G1)], "n_diff": len(diff), "diffs": [[i, x, y] for i, x, y in diff]}
    print("F5-003 vs F1-002", (a, b), len(G5), len(G1), "n_diff", len(diff), diff[:6])
G3 = g("r03-F3-003"); G31 = g("r01-F3-001")
from collections import Counter
cx = [x for x in G3 if x[0] == "cx"]
out["B"] = {"F3-003_gates": len(G3), "F3-001_gates": len(G31), "F3-003_cx": len(cx), "F3-001_cx": sum(1 for x in G31 if x[0] == "cx"),
            "F3-003_counts": dict(Counter(x[0] for x in G3)), "F3-001_counts": dict(Counter(x[0] for x in G31)),
            "cx_controls_outer": dict(Counter(x[1][0] for x in cx if x[1][0] >= 12)), "any_target_outer": any(q >= 12 for x in G3 for q in (x[1][1:] if x[0] == "cx" else x[1]) ),
            "any_1q_on_outer": any(len(x[1]) == 1 and x[1][0] >= 12 for x in G3)}
print(out["B"])
# bit meaning: in own codes qubit 12+3c+k  <-> site_bits(j1,j2,J) bit k of outer link-pair c; which spin-network labels have bit13/14 set?
n13 = sum(1 for c in OS.mine if (c >> 13) & 1); n14 = sum(1 for c in OS.mine if (c >> 14) & 1)
out["C"] = {"states_with_q13_set": n13, "states_with_q14_set": n14, "outer_qubits_read": sorted({x[1][0] for x in cx if x[1][0] >= 12})}
print(out["C"])
json.dump(out, open(ROOT / "results/tester/441/gates_f1.json", "w"), indent=1)
