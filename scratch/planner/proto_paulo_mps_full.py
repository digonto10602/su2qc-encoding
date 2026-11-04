"""Planner prototype: Paulo's compiled circuit on all 625 inner codes via Aer MPS (truncation 0, memory check
overridden) + own contraction; compare with exp(+i beta (TrW + h.c.)), beta = 1, Paulo basis/codec."""
import math, sys, time
import numpy as np
from scipy.linalg import expm
from qiskit import qasm3, QuantumCircuit, transpile
from qiskit_aer import AerSimulator
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/scratch/planner")
from proto_m0 import LinkSpace, plaquette_W
QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
base = qasm3.load(QASM); n = base.num_qubits
def code_of(p):
    if p == 0: return 0
    m, mp = {1: (1, 1), 2: (1, 0), 3: (0, 1), 4: (0, 0)}[p]
    return mp | (m << 1) | (1 << 2)
link_codes = [code_of(p) for p in range(5)]
codes = [sum(link_codes[(idx // 5 ** l) % 5] << (3 * l) for l in range(4)) for idx in range(625)]
def mps_amp(mps, bits):
    gam, lam = mps; v = None
    for q in range(n):
        A = np.asarray(gam[q][(bits >> q) & 1]); v = A[0] if v is None else v @ A
        if q < n - 1: v = v * np.asarray(lam[q])
    return complex(np.asarray(v).ravel()[0])
sim = AerSimulator(method="matrix_product_state", matrix_product_state_truncation_threshold=0.0, max_memory_mb=200_000_000)
t0 = time.time(); M = np.zeros((625, 625), complex); maxbond = 0
for col, code in enumerate(codes):
    qc = QuantumCircuit(n)
    for b in range(12):
        if (code >> b) & 1: qc.x(b)
    qc.compose(base, qubits=range(n), inplace=True); qc.save_matrix_product_state(label="mps")
    mps = sim.run(transpile(qc, sim)).result().data()["mps"]
    maxbond = max(maxbond, max(np.asarray(l).shape[0] for l in mps[1]))
    for row, c2 in enumerate(codes): M[row, col] = mps_amp(mps, c2)
print(f"625 inputs via Aer MPS: {time.time()-t0:.0f}s; max bond dim {maxbond}; min column norm on codes {np.linalg.norm(M, axis=0).min():.12f}")
ls = LinkSpace(0.5); W_cg = plaquette_W(ls)
perm = (0, 4, 3, 2, 1); signs = (1, 1, -1, -1, 1); V = np.zeros((5, 5))
for i in range(5): V[perm[i], i] = signs[i]
V4 = np.array([[1.0]])
for l in reversed(range(4)): V4 = np.kron(V4, V)
W_P = V4 @ W_cg @ V4.T
for sgn in (+1, -1):
    for beta in (0.5, 1.0, 2.0):
        T = expm(sgn * 1j * beta * (W_P + W_P.conj().T)); ov = np.trace(T.conj().T @ M); ph = ov / abs(ov)
        print(f"exp({'+' if sgn>0 else '-'}i beta (TrW+h.c.)), beta={beta}: op-norm error after one global phase = {np.linalg.norm(M - ph*T, 2):.3e}")
np.save("/home/digimonk/Projects/su2qc-encoding/scratch/planner/paulo_M_mps.npy", M)
