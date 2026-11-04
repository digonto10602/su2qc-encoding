"""Planner prototype: macro-gate lowering costs at level 0, pygridsynth T-count band, Qiskit CT PM determinism.
Run in the coding env:  python scratch/planner/proto_metrics.py
"""
import math, time
import numpy as np
import mpmath
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import MCXGate
from qiskit.transpiler import generate_preset_clifford_t_pass_manager
from pygridsynth.gridsynth import gridsynth_gates

LOGICAL_BASIS = ["cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz"]
SEED = 20261104

def classify(qc):
    c = qc.count_ops()
    n_rot = 0; t_fixed = c.get("t", 0) + c.get("tdg", 0)
    for inst in qc.data:
        if inst.operation.name == "rz":
            th = float(inst.operation.params[0])
            k = th / (math.pi / 4)
            if abs(k - round(k)) < 1e-9:
                if round(k) % 2 == 1:
                    t_fixed += 1
            else:
                n_rot += 1
    return dict(cx=c.get("cx", 0), depth=qc.depth(), n_rot=n_rot, t_fixed=t_fixed, ops=dict(c))

def lower(qc):
    return transpile(qc, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED)

theta = 0.37
cases = {}
qc = QuantumCircuit(3); qc.ccx(0, 1, 2); cases["ccx"] = qc
qc = QuantumCircuit(3); qc.rccx(0, 1, 2); cases["rccx"] = qc
qc = QuantumCircuit(2); qc.swap(0, 1); cases["swap"] = qc
qc = QuantumCircuit(2); qc.ch(0, 1); cases["ch"] = qc
qc = QuantumCircuit(2); qc.crz(theta, 0, 1); cases["crz"] = qc
qc = QuantumCircuit(2); qc.crx(theta, 0, 1); cases["crx"] = qc
qc = QuantumCircuit(2); qc.cp(theta, 0, 1); cases["cp"] = qc
qc = QuantumCircuit(2); qc.cz(0, 1); cases["cz"] = qc
qc = QuantumCircuit(1); qc.p(theta, 0); cases["p"] = qc
qc = QuantumCircuit(1); qc.sx(0); cases["sx"] = qc
qc = QuantumCircuit(3); qc.ccz(0, 1, 2); cases["ccz"] = qc
qc = QuantumCircuit(4); qc.append(MCXGate(3), [0, 1, 2, 3]); cases["mcx3"] = qc
qc = QuantumCircuit(5); qc.append(MCXGate(4), [0, 1, 2, 3, 4]); cases["mcx4"] = qc
qc = QuantumCircuit(3); qc.mcrx(theta, [0, 1], 2); cases["mcrx2"] = qc
for name, qc in cases.items():
    low = lower(qc)
    print(f"{name:6s} level-0 lowering: {classify(low)}")

# pygridsynth band
print("\npygridsynth T per rotation (angle, eps) -> T, word error")
def word_matrix(word):
    M = {"H": np.array([[1, 1], [1, -1]]) / math.sqrt(2), "S": np.diag([1, 1j]), "T": np.diag([1, np.exp(1j * math.pi / 4)]),
         "X": np.array([[0, 1], [1, 0]]), "W": np.eye(2) * np.exp(1j * math.pi / 4)}
    U = np.eye(2, dtype=complex)
    for ch in word: U = U @ M[ch]
    return U
def phase_dist(A, B):
    ov = np.trace(B.conj().T @ A); ph = ov / abs(ov)
    return float(np.linalg.norm(A - ph * B, 2))
angles = [0.37, 0.61, -0.555, 1.7, 2.0 * 0.61, -3 * 0.37 / 4]
t0 = time.time()
for eps in (1e-4, 1e-6, 1e-8, 1e-10):
    row = []
    for th in angles:
        w = gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps)))
        err = phase_dist(word_matrix(w), np.diag([np.exp(-0.5j * th), np.exp(0.5j * th)]))
        row.append((w.count("T"), f"{err:.1e}"))
    print(f"  eps={eps:g}: 3log2(1/eps)={3*math.log2(1/eps):.1f}  ->", row)
print(f"  ({time.time()-t0:.1f}s)")

# Qiskit CT pass manager on a single rz
print("\nQiskit Clifford+T PM on rz(theta):")
for eps in (1e-6, 1e-10):
    for th in angles[:3]:
        outs = []
        for rep in range(2):
            pm = generate_preset_clifford_t_pass_manager(basis_gates=["cx", "h", "s", "sdg", "t", "tdg"], optimization_level=3,
                                                         rz_synthesis_config={"rz_synthesis_error": eps, "rz_cache_error": eps / 10},
                                                         seed_transpiler=12345)
            qc = QuantumCircuit(1); qc.rz(th, 0)
            out = pm.run(qc); c = out.count_ops(); outs.append(dict(c))
        print(f"  eps={eps:g} theta={th}: T={outs[0].get('t',0)+outs[0].get('tdg',0)} ops={outs[0]} deterministic={outs[0]==outs[1]}")
