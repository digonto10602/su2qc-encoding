"""Planner prototype: run Paulo's compiled 34-qubit Clifford+T circuit (beta = 1, i.e. alpha_P = 2) on the 625
inner codes with a dict-state simulator and compare with exp(+i beta (TrW + TrW^dag)) in Paulo's basis / codec.
Run in the coding env:  python scratch/planner/proto_paulo_check.py
"""
import math, sys, time, itertools
import numpy as np
from qiskit import qasm3
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/scratch/planner")
from proto_m0 import LinkSpace, plaquette_W, paulo_U

QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
qc = qasm3.load(QASM)
n = qc.num_qubits
qubit_index = {q: i for i, q in enumerate(qc.qubits)}
gates = [(inst.operation.name, [qubit_index[q] for q in inst.qubits]) for inst in qc.data]
print("qubits", n, "gates", len(gates), qc.count_ops())

H = np.array([[1, 1], [1, -1]]) / math.sqrt(2)
PH = {"s": 1j, "sdg": -1j, "t": np.exp(1j * math.pi / 4), "tdg": np.exp(-1j * math.pi / 4)}

def run(state):
    for name, qs in gates:
        if name == "cx":
            c, t = qs; mc, mt = 1 << c, 1 << t
            state = {(k ^ mt if k & mc else k): v for k, v in state.items()}
        elif name == "h":
            m = 1 << qs[0]; new = {}
            for k, v in state.items():
                b = (k >> qs[0]) & 1
                k0, k1 = k & ~m, k | m
                new[k0] = new.get(k0, 0) + v * H[0, b]
                new[k1] = new.get(k1, 0) + v * H[1, b]
            state = {k: v for k, v in new.items() if abs(v) > 1e-13}
        elif name in PH:
            m = 1 << qs[0]; ph = PH[name]
            state = {k: (v * ph if k & m else v) for k, v in state.items()}
        else:
            raise ValueError(name)
    return state

# codec: link l at qubits (3l, 3l+1, 3l+2) = (m', m, j); Paulo basis order [0, ++, +-, -+, --]; + -> bit 1
def code_of(pstate):  # pstate index in Paulo order
    if pstate == 0: return 0
    m, mp = {1: (1, 1), 2: (1, 0), 3: (0, 1), 4: (0, 0)}[pstate]
    return (mp << 0) | (m << 1) | (1 << 2)
link_codes = [code_of(p) for p in range(5)]
codes = []  # inner index (link0 least significant, Paulo order) -> 12-bit code
for s in itertools.product(range(5), repeat=4):   # s[3] s[2] s[1] s[0]? use link-major little endian: idx = sum s_l 5^l
    pass
codes = {}
for idx in range(625):
    s = [(idx // 5 ** l) % 5 for l in range(4)]
    codes[idx] = sum(link_codes[s[l]] << (3 * l) for l in range(4))
code_to_idx = {v: k for k, v in codes.items()}

t0 = time.time()
M = np.zeros((625, 625), complex); leak = np.zeros(625)
for idx in range(625):
    out = run({codes[idx]: 1.0 + 0j})
    for k, v in out.items():
        if k >> 12 == 0 and (k & 0xFFF) in code_to_idx:
            M[code_to_idx[k & 0xFFF], idx] = v
        else:
            leak[idx] += abs(v) ** 2
print(f"simulated 625 inputs in {time.time()-t0:.1f}s; max leak = {leak.max():.2e}")

# target: V_P W V_P^T per link (Paulo basis), exp(+i beta (TrW + TrW^dag)), beta = 1
ls = LinkSpace(0.5)
W_cg = plaquette_W(ls)
perm = (0, 4, 3, 2, 1); signs = (1, 1, -1, -1, 1)
V = np.zeros((5, 5))
for i in range(5): V[perm[i], i] = signs[i]
# W_cg uses CG indices on each link; convert to Paulo indices: W_P = V4 W_cg V4^T with V4 = kron over links (link0 least significant)
V4 = np.array([[1.0]])
for l in reversed(range(4)): V4 = np.kron(V4, V)
# check V4 maps CG index -> Paulo index consistently: V_{perm[i], i} => V^T maps CG->Paulo? Both orderings tried below.
for name, VV in (("V4", V4), ("V4^T", V4.T)):
    W_P = VV @ W_cg @ VV.T
    from scipy.linalg import expm
    beta = 1.0
    target = expm(1j * beta * (W_P + W_P.conj().T))
    ov = np.trace(target.conj().T @ M); ph = ov / abs(ov)
    err = np.linalg.norm(M - ph * target, 2)
    print(f"{name}: op-norm error after one global phase = {err:.3e}  (phase {np.angle(ph):.4f})")
    # also test the opposite sign of beta
    target2 = expm(-1j * beta * (W_P + W_P.conj().T))
    ov = np.trace(target2.conj().T @ M); ph = ov / abs(ov)
    print(f"{name}: with exp(-i beta ...): error = {np.linalg.norm(M - ph * target2, 2):.3e}")
