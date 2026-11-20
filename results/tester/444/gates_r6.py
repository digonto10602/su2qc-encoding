"""Tester 444: structural claims of round 6 (F3-006 = parent F3-005 frame + a different 22-toggle walk) and an independent depth_CT recount.
(A) F3-005 vs F3-004: same multiset of gates?  Which relative orders changed (inversions) and does every inverted pair COMMUTE (matrix test on the union of qubits)?
    Same walk (the sequence of cx onto q0 between the h(0) pair with the rz after each)?  Position of the four p(-3alpha/4) gates; per-qubit gates between old and new place.
(B) F5-005 vs F3-004: positions that differ; walk identical; collapse cx(9,3) -> cx(0,3) (and inverse).
(C) F1-004 vs F3-004 frame: Margolus second-control wires (D = (3, 0, 1)); outer reads; counts; vs F1-002 parent (is it really a descendant of F1-002? claims 'F3 frame').
(D) own depth_CT recount: own lowering (decompose), rz/p -> pygridsynth word (own letters), qiskit depth; compare with archive depth_ct for all programs.
No RNG.  Run: PYTHONPATH=src python results/tester/444/gates_r5.py -> results/tester/444/gates_r5.json"""
import json, sys, subprocess, pathlib, warnings, math
warnings.filterwarnings("ignore")
from collections import Counter
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
import mpmath, pygridsynth
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/444"))
import own_sparse as OS
from su2plaq.compress import evaluate as E
from su2plaq.lsh import loop as LL
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "seed": None}
P = OS.PROGS
def circ(eid, a=0.37, b=0.61): return E.load_program(str(ROOT / "compress/programs/lsh" / P[eid])).build(LL.spec().with_angles(a, b)).circuit()
def sig(x): return (x[0], tuple(x[1]), tuple(round(v, 9) for v in x[2]))
def gl(qc): return OS.gates_of(qc)

def matrix_of(x, qubits):
    qc = QuantumCircuit(len(qubits))
    m = {q: i for i, q in enumerate(qubits)}
    getattr(qc, x[0])(*x[2], *[m[q] for q in x[1]]) if x[2] else getattr(qc, x[0])(*[m[q] for q in x[1]])
    return Operator(qc).data
def commute(x, y):
    qs = sorted(set(x[1]) | set(y[1]))
    A, B = matrix_of(x, qs), matrix_of(y, qs)
    return float(np.abs(A @ B - B @ A).max())

def walk(G):
    """the pivot window: gates on q0 strictly between the two h(0) gates, as a list of ('cx', src) / ('rz', angle)."""
    hs = [i for i, x in enumerate(G) if x[0] == "h" and x[1] == [0]]
    i0, i1 = hs[0], hs[1]
    w = []
    for x in G[i0 + 1:i1]:
        if 0 in x[1]:
            w.append(("cx", x[1][0]) if x[0] == "cx" else (x[0], round(x[2][0], 9)))
    return w


# ---------------- (A) F3-006 vs F3-005: same frame outside the walk window; different walk
def window(G):
    hs = [i for i, x in enumerate(G) if x[0] == "h" and x[1] == [0]]
    return hs[0], hs[1]
out["A"] = {}
for (a, b) in [(0.37, 0.61), (0.91, 0.23), (1.7, 1.0)]:
    A5, A6 = gl(circ("r05-F3-005", a, b)), gl(circ("r06-F3-006", a, b))
    i5, j5 = window(A5); i6, j6 = window(A6)
    pre5, post5, pre6, post6 = [sig(x) for x in A5[:i5]], [sig(x) for x in A5[j5 + 1:]], [sig(x) for x in A6[:i6]], [sig(x) for x in A6[j6 + 1:]]
    w5, w6 = A5[i5 + 1:j5], A6[i6 + 1:j6]
    cx6 = [x[1][0] for x in w6 if x[0] == "cx" and x[1][1] == 0]; cx5 = [x[1][0] for x in w5 if x[0] == "cx" and x[1][1] == 0]
    rz6 = [round(x[2][0] / b, 9) for x in w6 if x[0] == "rz"]; rz5 = [round(x[2][0] / b, 9) for x in w5 if x[0] == "rz"]
    out["A"][f"{a},{b}"] = {"prefix_equal": pre5 == pre6, "suffix_equal": post5 == post6, "n_prefix": len(pre6), "n_suffix": len(post6),
                            "window_cx_onto_q0": [len(cx5), len(cx6)], "window_rz": [len(rz5), len(rz6)], "window_rz_coeffs_F3-006": rz6,
                            "other_gates_in_window": sorted({x[0] for x in w6 if not (x[0] == "cx" and x[1][1] == 0) and x[0] != "rz"}),
                            "walks_differ": cx5 != cx6, "cx_sources_F3-006": cx6, "cx_sources_F3-005": cx5}
    print("A", (a, b), {k: v for k, v in out["A"][f"{a},{b}"].items() if k not in ("cx_sources_F3-006", "cx_sources_F3-005", "window_rz_coeffs_F3-006")}, flush=True)
A6 = gl(circ("r06-F3-006")); A5 = gl(circ("r05-F3-005"))
out["A"]["cx_total"] = [sum(1 for x in A5 if x[0] == "cx"), sum(1 for x in A6 if x[0] == "cx")]
out["A"]["cx_outside_window_F3-006"] = sum(1 for k, x in enumerate(A6) if x[0] == "cx" and not (window(A6)[0] < k < window(A6)[1]))
out["A"]["gate_counts_F3-006"] = dict(Counter(x[0] for x in A6))
gen = {1: 1, 4: 2, 7: 4, 10: 8, 9: 16, 13: 32, 14: 48}
i6, j6 = window(A6); x = 16; pts = [16]
for y in A6[i6 + 1:j6]:
    if y[0] == "cx" and y[1][1] == 0: x ^= gen[y[1][0]]; pts.append(x)
q5 = [((p & 15) | (((p >> 5) & 1) << 4)) for p in pts]
out["A"]["F3-006_points"] = pts; out["A"]["F3-006_q5_projection"] = q5; out["A"]["F3-006_end_point"] = pts[-1]
doc = [int(t) for t in "0 1 3 7 3 19 23 31 30 14 15 11 27 11 9 25 29 13 5 21 20 4 0".split()]
out["A"]["docstring_q5_walk_equals_reversed_or_forward"] = (q5 == doc or q5 == doc[::-1])
print("A walk pts", pts, "q5", q5, "doc", doc, out["A"]["docstring_q5_walk_equals_reversed_or_forward"])

# ---------------- (D) own depth recount
BASIS = {"cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz", "p", "u1", "u2", "u3", "u", "id", "y"}
EX = {0: "", 1: "T", 2: "S", 3: "ST", 4: "SS", 5: "SST", 6: "SSS", 7: "SSST"}
def lower(qc):
    q = qc
    for _ in range(12):
        if {i.operation.name for i in q.data} <= BASIS: return q
        q = q.decompose()
    raise RuntimeError
def depth_ct(qc, eps=1e-6):
    low = lower(qc); q = QuantumCircuit(low.num_qubits)
    for ins in low.data:
        nm = ins.operation.name; qs = [low.find_bit(b).index for b in ins.qubits]
        if nm in ("rz", "p", "u1"):
            th = float(ins.operation.params[0]); k = th / (math.pi / 4)
            w = EX[int(round(k)) % 8] if abs(k - round(k)) < 1e-9 else str(pygridsynth.gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps))))
            for ch in reversed(w):
                if ch == "H": q.h(qs[0])
                elif ch == "S": q.s(qs[0])
                elif ch == "T": q.t(qs[0])
                elif ch == "X": q.h(qs[0]); q.s(qs[0]); q.s(qs[0]); q.h(qs[0])
                elif ch == "W": pass
                else: raise ValueError(ch)
        else:
            q.append(ins.operation, qs)
    return q.depth()
out["D"] = {}
for eid in ("r06-F3-006", "r05-F3-005", "r04-F3-004"):
    ent = json.load(open(ROOT / f"compress/archive/lsh/entries/{eid}.json"))
    d = depth_ct(circ(eid))
    out["D"][eid] = {"own_depth_ct": d, "archive_depth_ct": ent["key"][2], "equal": d == ent["key"][2]}
    print("D", eid, d, ent["key"][2], flush=True)
json.dump(out, open(ROOT / "results/tester/444/gates_r6.json", "w"), indent=1, default=lambda o: str(o))
