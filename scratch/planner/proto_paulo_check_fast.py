"""Planner prototype (vectorised): Paulo's compiled 34-qubit Clifford+T circuit (beta = 1) on the 625 inner codes,
batched COO simulation (keys, cols, amps) — the design of su2plaq.evaluate.sparse_sim. Compare with
exp(+i beta (TrW + TrW^dag)) in Paulo's basis/codec up to one global phase.
Run in the coding env:  python scratch/planner/proto_paulo_check_fast.py
"""
import math, sys, time
import numpy as np
from scipy.linalg import expm
from qiskit import qasm3
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/scratch/planner")
from proto_m0 import LinkSpace, plaquette_W

QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
qc = qasm3.load(QASM)
qi = {q: i for i, q in enumerate(qc.qubits)}
gates = [(inst.operation.name, [qi[q] for q in inst.qubits]) for inst in qc.data]
PH = {"s": 1j, "sdg": -1j, "t": np.exp(1j * math.pi / 4), "tdg": np.exp(-1j * math.pi / 4), "z": -1.0}
R2 = 1 / math.sqrt(2)

def coalesce(keys, cols, amps):
    comb = keys.astype(np.int64) * 1024 + cols
    u, inv = np.unique(comb, return_inverse=True)
    a = np.zeros(len(u), complex); np.add.at(a, inv, amps)
    keep = np.abs(a) > 1e-14
    u = u[keep]; a = a[keep]
    return u // 1024, (u % 1024).astype(np.int32), a

def run(inputs):
    keys = np.array(inputs, dtype=np.int64); cols = np.arange(len(inputs), dtype=np.int32); amps = np.ones(len(inputs), complex)
    for name, qs in gates:
        if name == "cx":
            mc, mt = 1 << qs[0], 1 << qs[1]
            keys = np.where(keys & mc != 0, keys ^ mt, keys)
        elif name in PH:
            m = 1 << qs[0]; amps = np.where(keys & m != 0, amps * PH[name], amps)
        elif name == "x":
            keys = keys ^ (1 << qs[0])
        elif name == "h":
            m = 1 << qs[0]; b = (keys & m) != 0
            k0 = keys & ~m; k1 = keys | m
            keys = np.concatenate([k0, k1]); cols = np.concatenate([cols, cols])
            amps = np.concatenate([amps * R2, np.where(b, -amps * R2, amps * R2)])
            keys, cols, amps = coalesce(keys, cols, amps)
        else:
            raise ValueError(name)
    return keys, cols, amps

def code_of(p):
    if p == 0: return 0
    m, mp = {1: (1, 1), 2: (1, 0), 3: (0, 1), 4: (0, 0)}[p]
    return mp | (m << 1) | (1 << 2)
link_codes = [code_of(p) for p in range(5)]
codes = np.array([sum(link_codes[(idx // 5 ** l) % 5] << (3 * l) for l in range(4)) for idx in range(625)], dtype=np.int64)
code_to_idx = {int(c): i for i, c in enumerate(codes)}

t0 = time.time()
keys, cols, amps = run(codes)
print(f"batched run: {time.time()-t0:.1f}s, {len(keys)} output amplitudes")
M = np.zeros((625, 625), complex); leak = np.zeros(625)
for k, c, a in zip(keys, cols, amps):
    if (k >> 12) == 0 and int(k) in code_to_idx:
        M[code_to_idx[int(k)], c] = a
    else:
        leak[c] += abs(a) ** 2
print(f"max leak = {leak.max():.2e}")

ls = LinkSpace(0.5); W_cg = plaquette_W(ls)
perm = (0, 4, 3, 2, 1); signs = (1, 1, -1, -1, 1)
V = np.zeros((5, 5))
for i in range(5): V[perm[i], i] = signs[i]
V4 = np.array([[1.0]])
for l in reversed(range(4)): V4 = np.kron(V4, V)
for name, VV in (("V4", V4), ("V4^T", V4.T)):
    W_P = VV @ W_cg @ VV.T
    for sgn in (+1, -1):
        target = expm(sgn * 1j * 1.0 * (W_P + W_P.conj().T))
        ov = np.trace(target.conj().T @ M); ph = ov / abs(ov)
        err = np.linalg.norm(M - ph * target, 2)
        print(f"{name}, exp({'+' if sgn>0 else '-'}i beta (TrW+h.c.)), beta=1: op-norm error after one global phase = {err:.3e}")
# also: which beta fits best (scan) for the V4, + sign case
W_P = V4 @ W_cg @ V4.T
for beta in (0.5, 1.0, 2.0):
    target = expm(1j * beta * (W_P + W_P.conj().T)); ov = np.trace(target.conj().T @ M); ph = ov / abs(ov)
    print(f"  beta={beta}: error {np.linalg.norm(M - ph * target, 2):.3e}")
