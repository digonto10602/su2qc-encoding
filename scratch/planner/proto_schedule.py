"""Planner prototype: DAG scheduling of Paulo's compiled circuit to keep the sparse state small, then the check
against exp(+i beta (TrW + h.c.)).  Any topological order of the gate DAG is an equivalent circuit."""
import math, sys, time, heapq
import numpy as np
from scipy.linalg import expm
from qiskit import qasm3
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/scratch/planner")
from proto_m0 import LinkSpace, plaquette_W

QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
qc = qasm3.load(QASM); n = qc.num_qubits
qi = {q: i for i, q in enumerate(qc.qubits)}
gates = [(inst.operation.name, tuple(qi[q] for q in inst.qubits)) for inst in qc.data]
BRANCH = {"h"}

def schedule(gates, n):
    """topological order: non-branching ready gates first; then H on a qubit already open; then any H (fewest open)."""
    G = len(gates); succ = [[] for _ in range(G)]; indeg = [0] * G; last = [None] * n
    for g, (name, qs) in enumerate(gates):
        for q in qs:
            if last[q] is not None:
                succ[last[q]].append(g); indeg[g] += 1
            last[q] = g
    ready = [g for g in range(G) if indeg[g] == 0]
    open_q = set(); order = []
    while ready:
        nb = [g for g in ready if gates[g][0] not in BRANCH]
        if nb:
            g = min(nb)
        else:
            on_open = [g for g in ready if gates[g][1][0] in open_q]
            g = min(on_open) if on_open else min(ready)
        ready.remove(g); order.append(g)
        name, qs = gates[g]
        if name in BRANCH:
            q = qs[0]
            if q in open_q: open_q.discard(q)
            else: open_q.add(q)
        for s in succ[g]:
            indeg[s] -= 1
            if indeg[s] == 0: ready.append(s)
    assert len(order) == G
    return [gates[g] for g in order]

PH = {"s": 1j, "sdg": -1j, "t": np.exp(1j * math.pi / 4), "tdg": np.exp(-1j * math.pi / 4), "z": -1.0}
R2 = 1 / math.sqrt(2)
def coalesce(keys, cols, amps):
    comb = keys * 1024 + cols
    u, inv = np.unique(comb, return_inverse=True)
    a = np.zeros(len(u), complex); np.add.at(a, inv, amps)
    keep = np.abs(a) > 1e-14; u = u[keep]; a = a[keep]
    return u // 1024, (u % 1024).astype(np.int64), a
def run(gs, inputs):
    keys = np.array(inputs, dtype=np.int64); cols = np.arange(len(inputs), dtype=np.int64); amps = np.ones(len(inputs), complex)
    peak = 0
    for name, qs in gs:
        if name == "cx":
            mc, mt = 1 << qs[0], 1 << qs[1]; keys = np.where(keys & mc != 0, keys ^ mt, keys)
        elif name in PH:
            m = 1 << qs[0]; amps = np.where(keys & m != 0, amps * PH[name], amps)
        elif name == "x": keys = keys ^ (1 << qs[0])
        elif name == "h":
            m = 1 << qs[0]; b = (keys & m) != 0
            keys = np.concatenate([keys & ~m, keys | m]); cols = np.concatenate([cols, cols])
            amps = np.concatenate([amps * R2, np.where(b, -amps * R2, amps * R2)])
            keys, cols, amps = coalesce(keys, cols, amps)
        else: raise ValueError(name)
        peak = max(peak, len(keys))
    return keys, cols, amps, peak

def code_of(p):
    if p == 0: return 0
    m, mp = {1: (1, 1), 2: (1, 0), 3: (0, 1), 4: (0, 0)}[p]
    return mp | (m << 1) | (1 << 2)
link_codes = [code_of(p) for p in range(5)]
codes = np.array([sum(link_codes[(idx // 5 ** l) % 5] << (3 * l) for l in range(4)) for idx in range(625)], dtype=np.int64)
code_to_idx = {int(c): i for i, c in enumerate(codes)}

sched = schedule(gates, n)
t0 = time.time()
keys, cols, amps, peak = run(sched, codes)
print(f"scheduled batched run: {time.time()-t0:.1f}s, peak amplitudes {peak}, final {len(keys)}")
M = np.zeros((625, 625), complex); leak = np.zeros(625)
for k, c, a in zip(keys, cols, amps):
    if (k >> 12) == 0 and int(k) in code_to_idx: M[code_to_idx[int(k)], c] = a
    else: leak[c] += abs(a) ** 2
print(f"max leak = {leak.max():.2e}")
ls = LinkSpace(0.5); W_cg = plaquette_W(ls)
perm = (0, 4, 3, 2, 1); signs = (1, 1, -1, -1, 1)
V = np.zeros((5, 5))
for i in range(5): V[perm[i], i] = signs[i]
V4 = np.array([[1.0]])
for l in reversed(range(4)): V4 = np.kron(V4, V)
W_P = V4 @ W_cg @ V4.T
for sgn in (+1, -1):
    for beta in (0.5, 1.0, 2.0):
        target = expm(sgn * 1j * beta * (W_P + W_P.conj().T)); ov = np.trace(target.conj().T @ M); ph = ov / abs(ov)
        print(f"exp({'+' if sgn>0 else '-'}i beta (TrW+h.c.)), beta={beta}: op-norm error after one global phase = {np.linalg.norm(M - ph * target, 2):.3e}")
np.save("/home/digimonk/Projects/su2qc-encoding/scratch/planner/paulo_M.npy", M)
