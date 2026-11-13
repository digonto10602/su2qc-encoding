"""Tester 408 (d): the eight circuit seeds of su2plaq.lsh.loop.seed_circuit, own Aer check on all 433 physical states at a
non-nominal angle pair vs the route-B (6j) target U6(beta) UE(alpha) (inner electric), idle qubits dropped, + counts at nominal.
Usage: python tester-408-seeds.py [labels...]"""
import json, sys, subprocess, time
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import QuantumRegister
from qiskit_aer import AerSimulator
sys.path.insert(0, "src")
from su2plaq.exact.spinnet import labels as route_b_labels, h_magnetic_phys_6j, h_electric_6j
from su2plaq.lsh.operators import code_of_label
from su2plaq.lsh import loop as LP
from su2plaq.metrics.logical import logical_metrics
from su2plaq.metrics.cliffordt import t_table

labs = route_b_labels(jmax=0.5)
codes = np.array([code_of_label(l) for l in labs], dtype=np.int64); assert len(set(codes.tolist())) == 433
H6 = h_magnetic_phys_6j(labs); w, v = np.linalg.eigh(H6)
U6 = lambda b: (v * np.exp(-1j * b * w)) @ v.conj().T
hE = np.diag(h_electric_6j(labs, inner_only=True)); UE = lambda a: np.diag(np.exp(-1j * a * hE))
data, outer = codes & 0xFFF, codes >> 12
inner_set = sorted(set(data.tolist())); mask = np.zeros(4096, bool); mask[inner_set] = True
sim = AerSimulator(method="statevector", max_parallel_threads=1, max_parallel_experiments=1)

def simulate(qc):
    used = sorted({qc.find_bit(q).index for ins in qc.data for q in ins.qubits})
    outer_used = [q for q in used if 12 <= q < 24]
    keep = list(range(12)) + [q for q in used if q >= 24]           # data + ancillas (outer idle -> dropped)
    assert not outer_used, "outer qubits touched"
    m = {q: i for i, q in enumerate(keep)}
    sub = QuantumCircuit(len(keep))
    for ins in qc.data:
        sub.append(ins.operation, [m[qc.find_bit(q).index] for q in ins.qubits])
    sub.global_phase = qc.global_phase
    base = transpile(sub, basis_gates=["cx", "u", "rz", "h", "t", "tdg", "s", "sdg", "x", "z", "p", "ccx", "ry", "rx", "ccz", "swap", "cz", "u3", "u1", "u2", "sx"], optimization_level=0)
    n = len(keep); nanc = n - 12
    M = np.zeros((433, 433), complex); anc = np.zeros(433); inv = np.zeros(433); span = np.zeros(433)
    k = 0
    while k < 433:
        batch = range(k, min(433, k + 16)); circs = []
        for kk in batch:
            c = QuantumCircuit(n)
            for b in range(12):
                if (int(data[kk]) >> b) & 1: c.x(b)
            c.compose(base, inplace=True); c.save_statevector(); circs.append(c)
        res = sim.run(circs).result()
        for i, kk in enumerate(batch):
            sv = np.asarray(res.get_statevector(i)).reshape(1 << nanc, 1 << 12)
            anc[kk] = float(np.sum(np.abs(sv[1:]) ** 2)) if nanc else 0.0
            a0 = sv[0]; inv[kk] = float(np.sum(np.abs(a0[~mask]) ** 2))
            for j in range(433):
                if outer[j] == outer[kk]: M[j, kk] = a0[data[j]]
            blk = set(data[outer == outer[kk]].tolist()); span[kk] = float(sum(abs(a0[c]) ** 2 for c in inner_set if c not in blk))
        k += 16
    return M, anc, inv, span

def compare(M, T):
    ph = np.exp(1j * np.angle(np.trace(T.conj().T @ M))); D = M - ph * T
    return float(np.linalg.norm(D, 2)), float(np.abs(D).max()), float(np.linalg.norm(M.conj().T @ M - np.eye(433), 2))

labels = sys.argv[1:] or list(LP.CIRCUIT_SEEDS)
rows = []
for lab in labels:
    if lab == "general":
        rows.append({"label": lab, "skipped": "touches outer register (with_outer=True); covered by tester-403 step-exact and M8-S1 acceptance"}); continue
    t0 = time.time()
    nom = LP.seed_circuit(lab, 0.37, 0.61)
    lm = logical_metrics(nom); tt = {r["eps"]: r for r in t_table(nom, eps_list=(1e-6,))}[1e-6]
    alt = (0.83, 0.29)
    qc = LP.seed_circuit(lab, *alt)
    M, a, i, s = simulate(qc)
    e2, emax, unit = compare(M, U6(alt[1]) @ UE(alt[0]))
    ctrl = compare(M, U6(alt[1]))[0]          # control: wrong target (no electric layer) must be far
    r = {"label": lab, "cx": int(lm["cx"]), "n_rot": int(lm["n_rot"]), "t_fixed": int(lm["t_fixed"]), "T_eps1e-6": int(tt["t_total"]),
         "depth_CT": tt["depth_qiskit"], "qubits": nom.num_qubits, "alt_angles": alt, "op_norm_err": e2, "max_entry_err": emax, "unitarity_dev": unit,
         "anc_leak_max": float(a.max()), "invalid_data_leak_max": float(i.max()), "span_leak_max": float(s.max()), "control_wrong_target_err": ctrl,
         "seconds": time.time() - t0}
    print(r, flush=True); rows.append(r)
out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "dirty": True, "rows": rows}
json.dump(out, open("results/lsh_tester/tester-408-seeds.json", "w"), indent=1, default=str)
