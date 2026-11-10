import sys, pathlib, numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import aer_verify as A
from scipy.linalg import expm
root = pathlib.Path(sys.argv[1]); f = root/"compress/programs/spinnet/F5/001-tlean_7rot.py"
a, b = 0.37, 0.61
qc = A.build(f, a, b)
def block(qc):
    cols = A.run(qc); M = np.zeros((433,433), complex)
    for k,(nz,amp) in enumerate(cols):
        for i,z in zip(nz,amp):
            if not (int(i)>>16) and A.index.get(int(i)) is not None: M[A.index[int(i)],k] = z
    return M
def err(M, V):
    ov = np.trace(V.conj().T @ M); ph = ov/abs(ov); return float(np.linalg.norm(M-ph*V,2))
M = block(qc); V = A.target(a,b)
print("baseline", err(M,V))
print("target with -beta (wrong convention)", err(M, expm(+1j*b*A.HB) @ np.diag(np.exp(-1j*a*A.HE))))
print("target with order swapped U_E U_B", err(M, np.diag(np.exp(-1j*a*A.HE)) @ expm(-1j*b*A.HB)))
# perturb: first rz angle +1e-3
from qiskit import QuantumCircuit
q2 = qc.copy_empty_like(); done = False
for ins in qc.data:
    op = ins.operation
    if op.name == "rz" and not done: op = op.__class__(op.params[0] + 1e-3); done = True
    q2.append(op, ins.qubits)
print("first rz + 1e-3:", err(block(q2), V))
# extra X on a data qubit
q3 = qc.copy(); q3.x(0); print("extra x(0):", err(block(q3), V))
