"""Tester 443: structural claims of round 5 and an independent depth_CT recount.
(A) F3-005 vs F3-004: same multiset of gates?  Which relative orders changed (inversions) and does every inverted pair COMMUTE (matrix test on the union of qubits)?
    Same walk (the sequence of cx onto q0 between the h(0) pair with the rz after each)?  Position of the four p(-3alpha/4) gates; per-qubit gates between old and new place.
(B) F5-005 vs F3-004: positions that differ; walk identical; collapse cx(9,3) -> cx(0,3) (and inverse).
(C) F1-004 vs F3-004 frame: Margolus second-control wires (D = (3, 0, 1)); outer reads; counts; vs F1-002 parent (is it really a descendant of F1-002? claims 'F3 frame').
(D) own depth_CT recount: own lowering (decompose), rz/p -> pygridsynth word (own letters), qiskit depth; compare with archive depth_ct for all programs.
No RNG.  Run: PYTHONPATH=src python results/tester/443/gates_r5.py -> results/tester/443/gates_r5.json"""
import json, sys, subprocess, pathlib, warnings, math
warnings.filterwarnings("ignore")
from collections import Counter
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
import mpmath, pygridsynth
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/443"))
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

# ---------------- (A)
A4, A5 = gl(circ("r04-F3-004")), gl(circ("r05-F3-005"))
s4, s5 = [sig(x) for x in A4], [sig(x) for x in A5]
out["A"] = {"len": [len(A4), len(A5)], "multiset_equal": Counter(s4) == Counter(s5)}
# match gates by (sig, occurrence index)
def keyed(s):
    c = Counter(); r = []
    for x in s:
        r.append((x, c[x])); c[x] += 1
    return r
k4, k5 = keyed(s4), keyed(s5)
pos5 = {k: i for i, k in enumerate(k5)}
perm = [pos5[k] for k in k4]            # position in F3-005 of the gate that sits at i in F3-004
inv = [(i, j) for i in range(len(perm)) for j in range(i + 1, len(perm)) if perm[i] > perm[j]]
moved = sorted({g for pr in inv for g in pr})
maxcomm = 0.0; pairs_info = []
for i, j in inv:
    d = commute(A4[i], A4[j]); maxcomm = max(maxcomm, d)
    pairs_info.append((i, j, A4[i][0], A4[i][1], A4[j][0], A4[j][1], d))
pg = [i for i, x in enumerate(A4) if x[0] == "p"]
pg5 = [i for i, x in enumerate(A5) if x[0] == "p"]
out["A"].update({"n_inverted_pairs": len(inv), "max_commutator_norm_over_inverted_pairs": maxcomm,
                 "gates_involved_in_inversions": [(g, A4[g][0], A4[g][1]) for g in moved],
                 "p_positions_F3-004": pg, "p_qubits_F3-004": [A4[i][1][0] for i in pg], "p_positions_F3-005": pg5, "p_qubits_F3-005": [A5[i][1][0] for i in pg5],
                 "p_angles_over_alpha": sorted({round(A4[i][2][0] / 0.37, 6) for i in pg}),
                 "inverted_pair_kinds": dict(Counter(A4[i][0] + "<->" + A4[j][0] for i, j in inv)),
                 "walk_equal": walk(A4) == walk(A5), "walk_len": len(walk(A4)), "n_walk_cx": sum(1 for x in walk(A4) if x[0] == "cx"), "n_walk_rz": sum(1 for x in walk(A4) if x[0] == "rz")})
# the non-p gates keep their relative order?
nonp4 = [s for s, x in zip(s4, A4) if x[0] != "p"]; nonp5 = [s for s, x in zip(s5, A5) if x[0] != "p"]
out["A"]["non_p_gate_sequence_equal"] = nonp4 == nonp5
# per-qubit: gates on each moved p's qubit between old and new place
out["A"]["p_qubit_context"] = {}
for i in pg:
    q = A4[i][1][0]
    j = pos5[k4[i]]
    names4 = [x[0] + str(x[1]) for x in A4 if q in x[1]]
    names5 = [x[0] + str(x[1]) for x in A5 if q in x[1]]
    out["A"]["p_qubit_context"][f"q{q}"] = {"seq_F3-004": names4, "seq_F3-005": names5}
# three pairs: the same facts at the other pairs
out["A"]["pairs"] = {}
for (a, b) in OS.PAIRS:
    X, Y = gl(circ("r04-F3-004", a, b)), gl(circ("r05-F3-005", a, b))
    out["A"]["pairs"][f"{a},{b}"] = {"multiset_equal": Counter(sig(x) for x in X) == Counter(sig(y) for y in Y), "non_p_equal": [sig(x) for x in X if x[0] != "p"] == [sig(y) for y in Y if y[0] != "p"], "walk_equal": walk(X) == walk(Y)}
print("A", {k: v for k, v in out["A"].items() if k not in ("p_qubit_context",)})

# ---------------- (B)
B5 = gl(circ("r05-F5-005"))
diff = [(i, sig(x), sig(y)) for i, (x, y) in enumerate(zip(A4, B5)) if sig(x) != sig(y)]
out["B"] = {"len": [len(A4), len(B5)], "n_pos_diff": len(diff), "diffs": diff, "walk_equal": walk(A4) == walk(B5), "multiset_equal_F3-004": Counter(sig(x) for x in A4) == Counter(sig(y) for y in B5),
            "n_cx": sum(1 for x in B5 if x[0] == "cx")}
print("B", out["B"]["n_pos_diff"], diff)
# ---------------- (C)
C = gl(circ("r05-F1-004")); F1p = gl(circ("r02-F1-002"))
# Margolus Toffoli 'a' (the cx(a, t)) control wires, in the order they appear: cx(a,t) is the one between the two tdg/h blocks: find triples (cx(c,t), cx(a,t), cx(c,t))
trip = []
for i in range(len(C) - 2):
    x = C[i]
    pass
cxs = [(i, x[1]) for i, x in enumerate(C) if x[0] == "cx"]
# site Toffoli targets are q4, q7, q10 (l_nv of sites 1..3); every cx with target in {4,7,10} and control not in {...}? print them in order
tg = {4: 1, 7: 2, 10: 3}
tof = [(i, q) for i, q in cxs if q[1] in tg]
out["C"] = {"len": len(C), "gate_counts": dict(Counter(x[0] for x in C)), "cx_total": len(cxs),
            "cx_onto_targets_q4_q7_q10_index_control_target": tof,
            "outer_cx_controls": dict(Counter(q[0] for _, q in cxs if q[0] >= 12)),
            "outer_target_or_1q": any((x[0] == "cx" and x[1][1] >= 12) or (x[0] != "cx" and x[1][0] >= 12) for x in C),
            "walk_len": len(walk(C)), "walk_n_cx": sum(1 for x in walk(C) if x[0] == "cx"), "walk_n_rot": sum(1 for x in walk(C) if x[0] == "rz"),
            "walk_cx_sources": [x[1] for x in walk(C) if x[0] == "cx"],
            "F3-004 walk_cx_sources": [x[1] for x in walk(A4) if x[0] == "cx"]}
# F1-004 vs F3-004 frame: common prefix up to the first Margolus
pre = 0
while pre < min(len(C), len(A4)) and sig(C[pre]) == sig(A4[pre]): pre += 1
out["C"]["common_prefix_with_F3-004"] = pre
out["C"]["margolus_first_controls_F1-004"] = [q[0] for _, q in tof]
tof4 = [(i, x[1]) for i, x in enumerate(A4) if x[0] == "cx" and x[1][1] in tg]
out["C"]["cx_onto_q4_q7_q10_F3-004"] = tof4
print("C", {k: v for k, v in out["C"].items()})

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
for eid in P:
    ent = json.load(open(ROOT / f"compress/archive/lsh/entries/{eid}.json"))
    d = depth_ct(circ(eid))
    out["D"][eid] = {"own_depth_ct": d, "archive_depth_ct": ent["key"][2], "equal": d == ent["key"][2]}
    print("D", eid, d, ent["key"][2], flush=True)
json.dump(out, open(ROOT / "results/tester/443/gates_r5.json", "w"), indent=1, default=lambda o: str(o))
