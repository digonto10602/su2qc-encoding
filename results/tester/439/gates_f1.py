"""Tester 439: (A) compare the fully lowered gate lists (qiskit decompose to the basis, exact angles) of r02-F3-002 and r02-F5-002 against the
seed r00-seed-005 at three angle pairs: identical sequence?  Key and sha comparison.  (B) F1-002 claim: free CZ merges.  Build the F1-002 circuit
and the SAME circuit with the merge undone (CX(0,q) then separate CZ(0,q), time order as in the program's cx_cz/cz_cx docstring), run my own sparse engine
(all 433 states x 3 pairs + an unused pair), confirm both are exact; also check the algebraic identity CZ*CX == merged 4-gate block as 2-qubit unitaries (Operator).
Also negative control: drop the merge phase (use plain cx) -> must break exactness.  No RNG.
Run: PYTHONPATH=src taskset -c 0 tools/run-capped python results/tester/439/gates_f1.py -> results/tester/439/gates_f1.json"""
import json, sys, subprocess, hashlib, pathlib, warnings
warnings.filterwarnings("ignore")
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/439"))
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL

PAIRS = OS.PAIRS + [(1.13, 0.47)]
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
P = lambda rel: ROOT / "compress/programs/lsh" / rel
def lowered(rel, a, b):
    qc = E.load_program(str(P(rel))).build(LL.spec().with_angles(a, b)).circuit()
    return [(n, tuple(q), tuple(round(x, 12) for x in p)) for n, q, p in OS.gates_of(OS.lower(qc))], OS.gates_of(qc)
def native_equal(rel1, rel2, a, b):
    return lowered(rel1, a, b)[1] == lowered(rel2, a, b)[1]
seed = "seed/005-wrap_sn_headline.py"
out["A"] = {}
for eid, rel in (("r02-F3-002", OS.PROGS["r02-F3-002"]), ("r02-F5-002", OS.PROGS["r02-F5-002"]), ("r02-F1-002", OS.PROGS["r02-F1-002"]), ("r02-F4-002", OS.PROGS["r02-F4-002"])):
    r = {}
    for (a, b) in OS.PAIRS:
        L1, N1 = lowered(rel, a, b); L0, N0 = lowered(seed, a, b)
        r[f"{a},{b}"] = {"lowered_identical": L1 == L0, "native_identical": N1 == N0, "len_lowered": [len(L1), len(L0)], "len_native": [len(N1), len(N0)]}
        if L1 != L0 and len(L1) == len(L0):
            r[f"{a},{b}"]["first_diff_idx"] = next((i for i, (x, y) in enumerate(zip(L1, L0)) if x != y), None)
    out["A"][eid] = r
    print(eid, {k: (v["lowered_identical"], v["native_identical"]) for k, v in r.items()}, flush=True)
# (B) F1 CZ-merge
rel = OS.PROGS["r02-F1-002"]
def gates_f1(a, b):
    return OS.gates_of(E.load_program(str(P(rel))).build(LL.spec().with_angles(a, b)).circuit())
# identify the merged blocks: sequences (s,sdg,cx,s) / (sdg,sdg,cx,s) as in the program; expand each into CX + CZ separately
def unmerge(g):
    out_g = []; i = 0; n_cx_cz = n_cz_cx = 0
    while i < len(g):
        if i + 3 < len(g) and [x[0] for x in g[i:i + 4]] == ["s", "sdg", "cx", "s"] and g[i][1][0] == g[i + 2][1][0] == 0 and g[i + 1][1][0] == g[i + 2][1][1] == g[i + 3][1][0]:
            q = g[i + 2][1][1]; out_g += [("cx", [0, q], []), ("cz", [0, q], [])]; i += 4; n_cx_cz += 1; continue
        if i + 3 < len(g) and [x[0] for x in g[i:i + 4]] == ["sdg", "sdg", "cx", "s"] and g[i][1][0] == g[i + 2][1][0] == 0 and g[i + 1][1][0] == g[i + 2][1][1] == g[i + 3][1][0]:
            q = g[i + 2][1][1]; out_g += [("cz", [0, q], []), ("cx", [0, q], [])]; i += 4; n_cz_cx += 1; continue
        out_g.append(g[i]); i += 1
    return out_g, n_cx_cz, n_cz_cx
out["B"] = {"pairs": {}}
# 2-qubit identities
def U(gs, n=2):
    qc = QuantumCircuit(n)
    for nm, q, p in gs:
        getattr(qc, nm)(*p, *q)
    return Operator(qc)
cx_then_cz = U([("cx", [0, 1], []), ("cz", [0, 1], [])])
merged1 = U([("s", [0], []), ("sdg", [1], []), ("cx", [0, 1], []), ("s", [1], [])])
cz_then_cx = U([("cz", [0, 1], []), ("cx", [0, 1], [])])
merged2 = U([("sdg", [0], []), ("sdg", [1], []), ("cx", [0, 1], []), ("s", [1], [])])
out["B"]["identity_cx_then_cz"] = {"equal_up_to_phase": bool(cx_then_cz.equiv(merged1)), "equal_exact": bool(np.allclose(cx_then_cz.data, merged1.data))}
out["B"]["identity_cz_then_cx"] = {"equal_up_to_phase": bool(cz_then_cx.equiv(merged2)), "equal_exact": bool(np.allclose(cz_then_cx.data, merged2.data))}
print(out["B"])
for (a, b) in PAIRS:
    V = OS.target(a, b); g = gates_f1(a, b)
    gu, n1, n2 = unmerge(g)
    Mn, sn = OS.block(g); en, _ = OS.dist(Mn, V)
    Mu, su = OS.block(gu); eu, _ = OS.dist(Mu, V)
    # negative control: replace the merged blocks by a plain CX (no CZ)
    gp = []; i = 0
    while i < len(g):
        if i + 3 < len(g) and [x[0] for x in g[i:i + 4]] in (["s", "sdg", "cx", "s"], ["sdg", "sdg", "cx", "s"]) and g[i][1][0] == g[i + 2][1][0] == 0:
            gp.append(g[i + 2]); i += 4; continue
        gp.append(g[i]); i += 1
    Mp, _ = OS.block(gp); ep, _ = OS.dist(Mp, V)
    # also exactness with the trivial 433-block of the merged version at the exact pair: record cx of unmerged circuit (CZ = 0 CX)
    out["B"]["pairs"][f"{a},{b}"] = {"merged_err": en, "unmerged_err": eu, "plain_cx_no_cz_err": ep, "n_blocks_cx_cz": n1, "n_blocks_cz_cx": n2,
                                    "len_merged": len(g), "len_unmerged": len(gu), "stats_merged": sn, "stats_unmerged": su,
                                    "max_diff_merged_vs_unmerged_block": float(np.abs(Mn - Mu).max())}
    print((a, b), out["B"]["pairs"][f"{a},{b}"], flush=True)
json.dump(out, open(ROOT / "results/tester/439/gates_f1.json", "w"), indent=1, default=str)
