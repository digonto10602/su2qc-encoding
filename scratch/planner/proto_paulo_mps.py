"""Planner prototype: can qiskit-aer MPS run Paulo's compiled 34-qubit circuit on one basis input, and can we
extract the 625 code amplitudes (save_matrix_product_state + own contraction, and save_amplitudes for comparison)?
Run in the coding env:  python scratch/planner/proto_paulo_mps.py
"""
import math, sys, time
import numpy as np
from qiskit import qasm3, QuantumCircuit, transpile
from qiskit_aer import AerSimulator

QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
base = qasm3.load(QASM)
n = base.num_qubits

def code_of(p):
    if p == 0: return 0
    m, mp = {1: (1, 1), 2: (1, 0), 3: (0, 1), 4: (0, 0)}[p]
    return mp | (m << 1) | (1 << 2)
link_codes = [code_of(p) for p in range(5)]
codes = [sum(link_codes[(idx // 5 ** l) % 5] << (3 * l) for l in range(4)) for idx in range(625)]

def circuit_with_input(code, save):
    qc = QuantumCircuit(n)
    for b in range(12):
        if (code >> b) & 1: qc.x(b)
    qc.compose(base, qubits=range(n), inplace=True)
    if save == "mps":
        qc.save_matrix_product_state(label="mps")
    elif save == "amps":
        qc.save_amplitudes(codes, label="amps")   # amplitudes of |code> with ancillas 0 (code < 2^12)
    return qc

def contract_mps(mps, basis_int):
    """amplitude <basis_int| MPS>, Aer MPS format: (list of (G0, G1) per qubit, list of lambda vectors)."""
    gammas, lambdas = mps
    vec = None
    for q, (g0, g1) in enumerate(gammas):
        g = g1 if (basis_int >> q) & 1 else g0
        g = np.asarray(g)
        vec = g if vec is None else vec @ g
        if q < len(lambdas):
            vec = vec * np.asarray(lambdas[q])[None, :] if vec.ndim == 2 else vec * np.asarray(lambdas[q])
    return complex(np.asarray(vec).reshape(-1)[0]) if np.asarray(vec).size == 1 else np.asarray(vec)

sim = AerSimulator(method="matrix_product_state", matrix_product_state_truncation_threshold=0.0, max_memory_mb=200_000_000)
for code in (codes[0], codes[17]):
    t0 = time.time()
    qc = transpile(circuit_with_input(code, "mps"), sim)
    res = sim.run(qc).result()
    mps = res.data()["mps"]
    print(f"code {code}: MPS run {time.time()-t0:.1f}s; bond dims:", [np.asarray(l).shape for l in mps[1]][:8], "...")
    # contract to the 625 codes (ancillas 0)
    t0 = time.time()
    amps = np.array([contract_mps(mps, c) for c in codes])
    print(f"  contraction {time.time()-t0:.1f}s; sum|amp|^2 over codes = {np.sum(abs(amps)**2):.6f}; top: ",
          sorted([(abs(a), i) for i, a in enumerate(amps)], reverse=True)[:4])
    t0 = time.time()
    qc2 = transpile(circuit_with_input(code, "amps"), sim)
    res2 = sim.run(qc2).result(); a2 = np.asarray(res2.data()["amps"])
    print(f"  save_amplitudes {time.time()-t0:.1f}s: sum|amp|^2 = {np.sum(abs(a2)**2):.6f}; max |diff vs contraction| = {abs(a2-amps).max():.2e}")
