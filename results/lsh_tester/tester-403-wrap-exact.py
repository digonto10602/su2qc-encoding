"""Tester 403 (a): independent exactness check of wrap_spinnet on all 433 physical states.
Target: route-B 6j operator (su2plaq.exact.spinnet) in code order (code_of_label), NOT the LSH encoding's own target.
Circuit simulated with Aer statevector (batched), inputs = computational basis codes (data part only; outer idle)."""
import json, sys, subprocess, time
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from scipy.linalg import expm
from su2plaq.exact.spinnet import labels as route_b_labels, h_magnetic_phys_6j
from su2plaq.lsh.operators import code_of_label
import su2plaq.circuits.spinnet as CS
from su2plaq.circuits.lsh import wrap_spinnet, build_UB, build_step, build_UE

labs = route_b_labels(jmax=0.5)
codes = np.array([code_of_label(l) for l in labs], dtype=np.int64)
assert len(set(codes.tolist())) == 433
H6 = h_magnetic_phys_6j(labs)
w, v = np.linalg.eigh(H6)
def U6(beta): return (v * np.exp(-1j * beta * w)) @ v.conj().T
data = codes & 0xFFF; outer = codes >> 12
inner_set = sorted(set(data.tolist()))
assert len(inner_set) == 47
sim = AerSimulator(method="statevector", max_parallel_threads=4, max_parallel_experiments=4)

def simulate(qc):
    """returns dict state-> amplitude vector over data(12 bits) x ancilla register for each of 433 inputs.
    Output: M433 (433x433) matrix on physical codes, plus leakage numbers."""
    n = qc.num_qubits
    nanc = n - 12
    base = transpile(qc, basis_gates=["cx", "u", "rz", "h", "t", "tdg", "s", "sdg", "x", "z", "p", "ccx", "ry", "rx", "ccz", "swap", "cz", "u3", "u1", "u2", "sx"], optimization_level=0)
    M = np.zeros((433, 433), complex)
    anc_leak = np.zeros(433); inv_leak = np.zeros(433); span_leak = np.zeros(433); wrong_outer = np.zeros(433)
    idx_of = {c: k for k, c in enumerate(codes.tolist())}
    k = 0
    chunk = 40
    while k < 433:
        batch = range(k, min(433, k + chunk))
        circs = []
        for kk in batch:
            c = QuantumCircuit(n)
            d = int(data[kk])
            for b in range(12):
                if (d >> b) & 1: c.x(b)
            c.compose(base, inplace=True)
            c.save_statevector()
            circs.append(c)
        res = sim.run(circs).result()
        for i, kk in enumerate(batch):
            sv = np.asarray(res.get_statevector(i))
            # little endian: index = data | anc << 12
            sv = sv.reshape(1 << nanc, 1 << 12)
            anc_leak[kk] = float(np.sum(np.abs(sv[1:, :]) ** 2)) if nanc else 0.0
            a0 = sv[0]
            mask = np.zeros(1 << 12, bool); mask[inner_set] = True
            inv_leak[kk] = float(np.sum(np.abs(a0[~mask]) ** 2))
            for j in range(433):
                if outer[j] == outer[kk]:
                    M[j, kk] = a0[data[j]]
            # weight on inner data codes that are not physical in this outer block (Gauss/span leakage)
            blk = set(data[outer == outer[kk]].tolist())
            span_leak[kk] = float(sum(abs(a0[c]) ** 2 for c in inner_set if c not in blk))
        k += chunk
    return M, anc_leak, inv_leak, span_leak

def compare(M, T):
    ov = np.trace(T.conj().T @ M)
    ph = np.exp(1j * np.angle(ov))
    D = M - ph * T
    return float(np.linalg.norm(D, 2)), float(np.abs(D).max()), float(np.angle(ov)), float(np.linalg.norm(M.conj().T @ M - np.eye(433), 2))

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "dirty": True, "rows": []}
variants = [("general7", lambda b: CS.build_UB(b)), ("pairs9", lambda b: CS.trotter_v2_circuit("pairs9", b)),
            ("flags4", lambda b: CS.trotter_v2_circuit("flags4", b)), ("flags5", lambda b: CS.trotter_v2_circuit("flags5", b)),
            ("flags6", lambda b: CS.trotter_v2_circuit("flags6", b))]
betas = [float(x) for x in sys.argv[1:]] or [0.61]
for name, mk in variants:
    for beta in betas:
        t0 = time.time()
        sn = mk(beta)
        qc = wrap_spinnet(sn)
        # outer not read: no gates on qubits beyond d and ancillas (with_outer False) ; also with_outer variant
        qo = wrap_spinnet(sn, with_outer=True)
        touched_o = [qo.find_bit(q).index for inst in qo.data for q in inst.qubits if 12 <= qo.find_bit(q).index < 24]
        M, al, il, sl = simulate(qc)
        T = U6(beta)
        e2, emax, ph, unit = compare(M, T)
        row = dict(variant=name, beta=beta, nqubits=qc.num_qubits, op_norm_err=e2, max_entry_err=emax, global_phase=ph,
                   unitarity_dev=unit, anc_leak_prob_max=float(al.max()), invalid_data_leak_prob_max=float(il.max()),
                   span_leak_prob_max=float(sl.max()), outer_register_gates=len(touched_o), seconds=time.time() - t0)
        row['control_err_vs_identity']=compare(M, np.eye(433))[0]; row['control_err_vs_U(-beta)']=compare(M, U6(-beta))[0]
        row['control_err_vs_U(beta/2)']=compare(M, U6(beta/2))[0]
        print(row, flush=True)
        out["rows"].append(row)
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/lsh_tester/tester-403-wrap-exact.json", "w"), indent=1)
