"""Tester 442: phase-polynomial / walk comparison of the pivot walk (all gates acting on q0 between the h(0) pair) for the 71-CX F1/F5 circuits.
For each circuit: list of (cx source wires toggled, rz angle/beta) on q0 in the walk window; the parity trajectory (cumulative XOR of sources, as frozenset)
at every rz; the Walsh support {parity: summed coefficient}; counts.  Compare F1-003 / F5-004 with F1-002 / F5-003.  No RNG.
Run: PYTHONPATH=src python results/tester/442/walks.py -> results/tester/442/walks.json"""
import json, sys, pathlib, subprocess, warnings
warnings.filterwarnings("ignore")
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); sys.path.insert(0, str(ROOT / "results/tester/442"))
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
P = {"F1-002": "F1/002-free-end-walk-v.py", "F5-003": "F5/003-pivot-ladder-free-ends.py", "F1-003": "F1/003-euler-retour-pivot-ladder.py", "F5-004": "F5/004-reversed-walk-end-merge.py", "F3-003": "F3/003-3and-hk-free-end-mux.py", "F3-004": "F3/004-joint-sa-walk22.py"}
beta = 0.61
def walk(name, pivot=0):
    qc = E.load_program(str(ROOT / "compress/programs/lsh" / P[name])).build(LL.spec().with_angles(0.37, beta)).circuit()
    G = OS.gates_of(qc)
    hs = [i for i, g in enumerate(G) if g[0] == "h" and g[1] == [pivot]]
    # window between last-but-one... take the first/last h on pivot that bound the walk: choose the pair with max number of rz between
    best = None
    for a in range(len(hs)):
        for b in range(a + 1, len(hs)):
            n = sum(1 for g in G[hs[a]:hs[b]] if g[0] == "rz" and g[1] == [pivot])
            if best is None or n > best[0]: best = (n, hs[a], hs[b])
    n, i0, i1 = best
    win = [g for g in G[i0 + 1:i1] if (g[0] == "cx" and g[1][1] == pivot) or (g[0] == "rz" and g[1] == [pivot]) or pivot in g[1]]
    other = [g for g in G[i0 + 1:i1] if g not in win]
    par = frozenset(); seq = []; supp = {}; ntog = 0; toggles = []
    for g in win:
        if g[0] == "cx" and g[1][1] == pivot: par = par ^ {g[1][0]}; ntog += 1; toggles.append(g[1][0])
        elif g[0] == "rz":
            c = g[2][0] / beta; seq.append((sorted(par), round(c, 6))); supp[tuple(sorted(par))] = supp.get(tuple(sorted(par)), 0) + c
        else: return {"error": f"unexpected gate in window {g}"}
    return {"window": [i0, i1], "other_gates_in_window": len(other), "n_toggles_cx_in_window": ntog, "n_rz": len(seq), "toggle_sources": toggles,
            "walk": seq, "support": {str(k): round(v, 6) for k, v in sorted(supp.items())}, "support_size": len(supp), "final_parity": sorted(par)}
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None, "walks": {k: walk(k) for k in P}}
for k, w in out["walks"].items(): print(k, {x: w.get(x) for x in ("window", "other_gates_in_window", "n_toggles_cx_in_window", "n_rz", "support_size", "final_parity")})
S = {k: out["walks"][k]["support"] for k in P}
out["support_equal"] = {f"{a}~{b}": S[a] == S[b] for a, b in [("F1-003", "F1-002"), ("F5-004", "F5-003"), ("F1-003", "F5-003"), ("F5-004", "F1-002"), ("F5-004", "F1-003"), ("F5-003", "F1-002"), ("F3-004", "F3-003")]}
out["toggle_seq_equal"] = {f"{a}~{b}": out["walks"][a]["toggle_sources"] == out["walks"][b]["toggle_sources"] for a, b in [("F1-003", "F1-002"), ("F5-004", "F5-003"), ("F1-003", "F5-003"), ("F5-004", "F1-003")]}
out["toggle_seq_reversed_equal_F5-004_vs_F5-003"] = out["walks"]["F5-004"]["toggle_sources"] == out["walks"]["F5-003"]["toggle_sources"][::-1]
print(out["support_equal"], out["toggle_seq_equal"], out["toggle_seq_reversed_equal_F5-004_vs_F5-003"])
json.dump(out, open(ROOT / "results/tester/442/walks.json", "w"), indent=1)
