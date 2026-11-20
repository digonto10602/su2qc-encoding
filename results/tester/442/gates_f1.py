"""Tester 442: structural claims of round 4.
(A) F3-004 vs its parent F3-003: same frame gate for gate (common prefix / suffix of the native gate list; the differing middle = the walk)? counts, walk toggles.
(B) F1-003 and F5-004 vs EVERY existing archive entry of the LSH archive that is a 71-CX / 25-qubit circuit: gate-for-gate (same ordered list at each angle pair),
    DAG-equivalent (qiskit DAGCircuit equality = isomorphic with semantic node match, so reorderings of commuting-disjoint gates count as equal),
    same multiset of (name, qubits) gates, per-wire sequences equal.  Also positions of differences vs the claimed parent.
(C) F3-004 outer roles; F3-004 vs F3-003 with q13/q14 control counts.
No RNG.  Run: PYTHONPATH=src python results/tester/442/gates_f1.py -> results/tester/442/gates_f1.json"""
import json, sys, subprocess, pathlib, warnings, glob
warnings.filterwarnings("ignore")
from collections import Counter
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/442"))
import own_sparse as OS
from qiskit.converters import circuit_to_dag
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
# all archive entries' programs (valid ones)
progs = {}
for p in sorted(glob.glob(str(ROOT / "compress/archive/lsh/entries/*.json"))):
    e = json.load(open(p))
    if not e.get("valid") or not e.get("program_path") or not e["program_path"].endswith(".py"): continue
    progs[e["id"]] = (e["program_path"], e["key"])
def circ(eid, a=0.37, b=0.61): return E.load_program(str(ROOT / progs[eid][0])).build(LL.spec().with_angles(a, b)).circuit()
def gl(qc): return OS.gates_of(qc)
def sig(x): return (x[0], tuple(x[1]), tuple(round(v, 9) for v in x[2]))
def wires(G):
    w = {}
    for x in G:
        for q in x[1]: w.setdefault(q, []).append(sig(x))
    return w
out["A"] = {}
G4 = gl(circ("r04-F3-004")); G3 = gl(circ("r03-F3-003"))
pre = 0
while pre < min(len(G4), len(G3)) and sig(G4[pre]) == sig(G3[pre]): pre += 1
suf = 0
while suf < min(len(G4), len(G3)) - pre and sig(G4[-1 - suf]) == sig(G3[-1 - suf]): suf += 1
mid4, mid3 = G4[pre:len(G4) - suf], G3[pre:len(G3) - suf]
c = lambda G: dict(Counter(x[0] for x in G))
out["A"] = {"len": [len(G4), len(G3)], "common_prefix": pre, "common_suffix": suf, "mid_len_F3-004": len(mid4), "mid_len_F3-003": len(mid3),
            "mid_counts_F3-004": c(mid4), "mid_counts_F3-003": c(mid3), "all_counts_F3-004": c(G4), "all_counts_F3-003": c(G3),
            "mid_cx_sources_F3-004": [x[1][0] for x in mid4 if x[0] == "cx"], "mid_cx_sources_F3-003": [x[1][0] for x in mid3 if x[0] == "cx"],
            "n_cx_total": [sum(1 for x in G4 if x[0] == "cx"), sum(1 for x in G3 if x[0] == "cx")],
            "prefix_gate_for_gate_equal_incl_angles": True,
            "mid_first_gates_F3-004": [sig(x) for x in mid4[:6]], "mid_first_gates_F3-003": [sig(x) for x in mid3[:6]],
            "cx_controls_outer": dict(Counter(x[1][0] for x in G4 if x[0] == "cx" and x[1][0] >= 12)),
            "cx_controls_outer_F3-003": dict(Counter(x[1][0] for x in G3 if x[0] == "cx" and x[1][0] >= 12)),
            "any_target_outer": any(q >= 12 for x in G4 for q in (x[1][1:] if x[0] == "cx" else x[1])),
            "any_1q_on_outer": any(len(x[1]) == 1 and x[1][0] >= 12 for x in G4),
            "rz_p_angles_F3-004": sorted({round(x[2][0] / 0.61, 6) for x in G4 if x[0] == "rz"})}
print("A", {k: v for k, v in out["A"].items() if not k.startswith("mid_first")})
# frame equality when the walk is excised: compare gates before/after the walk region using pattern at three pairs
out["A"]["pairs"] = {}
for (a, b) in OS.PAIRS:
    X, Y = gl(circ("r04-F3-004", a, b)), gl(circ("r03-F3-003", a, b))
    p = 0
    while p < min(len(X), len(Y)) and sig(X[p]) == sig(Y[p]): p += 1
    s = 0
    while s < min(len(X), len(Y)) - p and sig(X[-1 - s]) == sig(Y[-1 - s]): s += 1
    out["A"]["pairs"][f"{a},{b}"] = {"prefix": p, "suffix": s, "len": [len(X), len(Y)]}
print(out["A"]["pairs"])

# (B)
out["B"] = {}
cand = ["r04-F1-003", "r04-F5-004"]
cmp_with = [e for e, (pth, k) in progs.items() if e not in cand and k[0] in (70, 71) ]  # all 70/71-CX entries incl. seeds
cmp_with += ["r04-F1-003", "r04-F5-004"]
for new in cand:
    out["B"][new] = {}
    for old in cmp_with:
        if old == new: continue
        res = {}
        for (a, b) in OS.PAIRS:
            X, Y = gl(circ(new, a, b)), gl(circ(old, a, b))
            nd = sum(1 for x, y in zip(X, Y) if sig(x) != sig(y)) if len(X) == len(Y) else None
            dagX, dagY = circuit_to_dag(circ(new, a, b)), circuit_to_dag(circ(old, a, b))
            res[f"{a},{b}"] = {"len": [len(X), len(Y)], "n_pos_diff": nd, "dag_equal": bool(dagX == dagY) if X and Y else None,
                               "multiset_equal": Counter(sig(x) for x in X) == Counter(sig(y) for y in Y), "wires_equal": wires(X) == wires(Y),
                               "n_wires_differing": sum(1 for q in set(wires(X)) | set(wires(Y)) if wires(X).get(q) != wires(Y).get(q))}
        out["B"][new][old] = res
        r0 = res["0.37,0.61"]
        print("B", new, "vs", old, progs[old][1], r0, flush=True)
# details vs claimed parent
for new, old in [("r04-F1-003", "r02-F1-002"), ("r04-F5-004", "r03-F5-003"), ("r04-F1-003", "r03-F5-003"), ("r04-F5-004", "r04-F1-003")]:
    X, Y = gl(circ(new)), gl(circ(old))
    diff = [[i, sig(x), sig(y)] for i, (x, y) in enumerate(zip(X, Y)) if sig(x) != sig(y)]
    out.setdefault("B_detail", {})[f"{new}_vs_{old}"] = {"len": [len(X), len(Y)], "n_diff": len(diff), "first_diffs": diff[:12],
        "counts_new": dict(Counter(x[0] for x in X)), "counts_old": dict(Counter(x[0] for x in Y))}
    print("Bdetail", new, old, len(X), len(Y), len(diff))
json.dump(out, open(ROOT / "results/tester/442/gates_f1.json", "w"), indent=1, default=str)
