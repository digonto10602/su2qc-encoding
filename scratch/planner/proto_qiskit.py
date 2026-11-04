"""Check the transpile pipeline reproducibility, statevector cost at 24 qubits, and the Pauli
decomposition size of a KS (jmax=1/2, 3 qubits/link binary) plaquette operator on 12 qubits."""
import time, sys, itertools
import numpy as np
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/scratch/planner")
from proto_m1 import KSLink
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp, Operator, Statevector
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.synthesis import LieTrotter
from qiskit_aer import AerSimulator

link = KSLink(0.5)
# embed 5 link states into 3 qubits: state index k -> |k> (binary), unused 5,6,7
d = 8
def embed(M):
    out = np.zeros((d, d), complex); out[:5, :5] = M; return out
U = {ab: embed(M) for ab, M in link.U.items()}
# plaquette on 4 links: Tr(U1 U2 U3^dag U4^dag)
def Udag(ab):
    a, b = ab; return U[(b, a)].conj().T
idx = [0.5, -0.5]
P = np.zeros((d ** 4, d ** 4), complex)
I = np.eye(d)
def k4(A, B, C, D):
    return np.kron(np.kron(np.kron(A, B), C), D)
for a, b, c, e in itertools.product(idx, repeat=4):
    P += k4(U[(a, b)], U[(b, c)], Udag((c, e)), Udag((e, a)))
P = P + P.conj().T  # Hermitian plaquette term (= 2 Re)
t0 = time.time()
op = SparsePauliOp.from_operator(Operator(P)).simplify(atol=1e-12)
print(f"Pauli terms in plaquette (12 qubits): {len(op)}  ({time.time()-t0:.1f}s)")
weights = [sum(1 for ch in str(p) if ch != 'I') for p in op.paulis]
print("weight histogram:", np.bincount(weights))
print("naive CNOT upper bound sum 2(w-1):", sum(2 * (w - 1) for w in weights if w > 1))
# Trotter circuit for exp(-i theta P) via PauliEvolutionGate, then transpile
qc = QuantumCircuit(12)
qc.append(PauliEvolutionGate(op, time=0.1, synthesis=LieTrotter()), range(12))
for seed in (1, 1, 2):
    t0 = time.time()
    tq = transpile(qc, basis_gates=["cx", "u"], optimization_level=1, seed_transpiler=seed)
    print(f"seed={seed}: cx={tq.count_ops().get('cx',0)} depth={tq.depth()} ({time.time()-t0:.1f}s)")
# statevector cost at 24 qubits
sim = AerSimulator(method="statevector", precision="double", max_parallel_threads=1)
qc24 = QuantumCircuit(24)
for i in range(24): qc24.h(i)
for i in range(23): qc24.cx(i, i + 1)
qc24.save_statevector()
t0 = time.time(); res = sim.run(transpile(qc24, sim)).result(); sv = res.get_statevector()
print(f"24-qubit statevector (1 thread): {time.time()-t0:.2f}s, dtype {np.asarray(sv).dtype}")
