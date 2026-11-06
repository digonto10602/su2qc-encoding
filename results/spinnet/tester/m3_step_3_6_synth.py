import json, sys, subprocess, time
import numpy as np, scipy.linalg as sl, scipy.sparse as sp
sys.path.insert(0, "src")
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.circuits.spinnet import trotter_v2_circuit
from su2plaq.exact.compare import gauge_align
from su2plaq.exact.operators import target as targetA
from su2plaq.su2.algebra import LinkSpace

OUT = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "seed": 12345}
enc = SpinNet(); basis = enc.basis
codes433 = np.array(enc._codes, dtype=np.int64)
index = {int(c): k for k, c in enumerate(codes433)}
inner = enc.inner_codes()
sim = AerSimulator(method="statevector", max_parallel_threads=10)


def specnorm(M): return float(np.linalg.norm(M, 2))
def err_phase(W, V):
    t = np.trace(V.conj().T @ W); ph = t / abs(t) if abs(t) > 0 else 1.0
    return specnorm(W - ph * V), complex(ph)


def run_states(qc, inputs, nq=None, chunk=20):
    """inputs: list of integers (computational basis states over all qubits of qc); returns array (len, 2^nq)."""
    nq = qc.num_qubits
    res = []
    for s0 in range(0, len(inputs), chunk):
        cs = []
        for x in inputs[s0:s0 + chunk]:
            c = QuantumCircuit(nq)
            for b in range(nq):
                if (x >> b) & 1: c.x(b)
            c.compose(qc, inplace=True)
            c.save_statevector()
            cs.append(c)
        t = transpile(cs, sim, optimization_level=0)
        r = sim.run(t).result()
        res += [np.asarray(r.data(i)["statevector"]) for i in range(len(t))]
    return np.array(res)


def matrix433_from_inner(qc_no_outer, ndata=8):
    """433x433 W from 47 inner-code runs of the circuit WITHOUT the outer register (valid because outer is a spectator;
    that is checked separately on the with_outer circuit).  Returns W, leak(max column), dirty(max column prob)."""
    nq = qc_no_outer.num_qubits
    V = run_states(qc_no_outer, [int(c) for c in inner])          # (47, 2^nq)
    pos = {int(c): i for i, c in enumerate(inner)}
    W = np.zeros((433, 433), complex); leak = np.zeros(433); dirty = np.zeros(433)
    # decompose: index = data (bits 0..7) + anc << 8
    nanc = nq - ndata
    Vr = V.reshape(len(inner), 1 << nanc, 256)                    # [i, anc, data]
    for k, c in enumerate(codes433):
        d, o = int(c) & 0xFF, int(c) >> 8
        vec = Vr[pos[d]]                                          # (anc, data)
        dirty[k] = float(np.sum(np.abs(vec[1:]) ** 2))
        amp = vec[0]
        tot_leak = 0.0
        for d2 in np.flatnonzero(np.abs(amp) > 1e-16):
            code2 = int(d2) | (o << 8)
            if code2 in index: W[index[code2], k] = amp[d2]
            else: tot_leak += abs(amp[d2]) ** 2
        leak[k] = np.sqrt(tot_leak)
    return W, float(leak.max()), float(dirty.max())


def gauss_setup():
    ls = LinkSpace(0.5); L, R = ls.generators()
    def apply(vec, link, M):
        o = {}
        for key, a in vec.items():
            s = (key // 5**link) % 5; base = key - s * 5**link
            for sp_ in range(M.shape[0]):
                m = M[sp_, s]
                if abs(m) > 0:
                    kk = base + sp_ * 5**link; o[kk] = o.get(kk, 0) + m * a
        return o
    rowkey = {}; rows, cols, vals = [], [], []
    for k, c in enumerate(codes433):
        ks, vs = enc.decode_state(np.array([c]), np.array([1.0 + 0j]))
        vec = dict(zip(ks.tolist(), vs.tolist()))
        for ci, corner in enumerate(basis.diagram.corners):
            for a in range(3):
                tot = {}
                for link, role in corner.ends:
                    r = apply(vec, link, L[a] if role == "out" else R[a])
                    for kk, v in r.items(): tot[kk] = tot.get(kk, 0) + v
                for kk, v in tot.items():
                    ridx = rowkey.setdefault((ci, a, kk), len(rowkey))
                    rows.append(ridx); cols.append(k); vals.append(v)
    G = sp.csr_matrix((vals, (rows, cols)), shape=(len(rowkey), 433))
    rowgrp = np.array([ (0) for _ in rowkey])
    grp = np.zeros(len(rowkey), dtype=np.int64)
    for (ci, a, kk), r in rowkey.items(): grp[r] = ci * 3 + a
    return G, grp
G, grp = gauss_setup()
Q = (G.conj().T @ G).toarray()          # sum over (corner, a) of ||G_ca psi||^2 = psi^dag Q psi
def gauss_res(W):
    r2 = np.einsum("ik,ij,jk->k", W.conj(), Q, W).real
    return float(np.sqrt(max(r2.max(), 0.0)))


import math
from su2plaq.metrics.cliffordt import synthesize
from su2plaq.metrics.logical import logical_metrics
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
HB = enc.h_magnetic()
def UB_t(b): return sl.expm(-1j * b * HB)
OUT["synth"] = []
cases = [("pairs9", 1e-4), ("pairs9", 1e-6), ("pairs9", 1e-8), ("flags4", 1e-4), ("flags4", 1e-6), ("flags4", 1e-8), ("flags5", 1e-6), ("flags6", 1e-6)]
b = 0.61
for sk, eps in cases:
    qc = trotter_v2_circuit(sk, b); lm = logical_metrics(qc)
    synth, info = synthesize(qc, eps)
    nrot = info["n_rot"]
    ops = dict(synth.count_ops())
    W, lk, dt = matrix433_from_inner(synth, 8)
    e, _ = err_phase(W, UB_t(b)); g = gauss_res(W)
    tol = synth_tolerances(nrot, eps)
    v = evaluate(synth, enc, enc.target("UB", None, b), **tol)
    row = {"skeleton": sk, "eps": eps, "n_rot": nrot, "T_in_synth": ops.get("t", 0) + ops.get("tdg", 0), "gate_set": sorted(ops),
           "my_block_error": e, "my_leak": lk, "my_dirty": dt, "my_gauss": g, "my_total(block+leak)": e + lk,
           "bound_N_eps": nrot * eps, "tol_err": tol["tol_err"], "tol_gauss": tol["tol_gauss"],
           "lib_ok": v.ok, "lib_op_norm_error": v.op_norm_error, "lib_block": v.block_error, "lib_leak": v.leak_amplitude, "lib_dropped": v.dropped_total,
           "lib_sum_parts": v.block_error + v.leak_amplitude + v.dropped_total, "lib_gauss": v.gauss_residual, "lib_certified": v.certified, "lib_engine": v.engine,
           "sum_measured_word_errors": info["error_measured_sum"], "info_bound": info["error_bound_sum"]}
    row["pass_my_total_le_N_eps"] = row["my_total(block+leak)"] <= nrot * eps
    row["pass_my_gauss_le_N_eps_plus_1e-9"] = g <= tol["tol_gauss"]
    row["pass_lib_equals_parts"] = abs(row["lib_op_norm_error"] - row["lib_sum_parts"]) <= 1e-12
    row["pass_my_le_sum_word_errors"] = row["my_block_error"] <= info["error_measured_sum"] + 1e-12
    OUT["synth"].append(row); print(row, flush=True)
# outer-register physical evaluation of the synthesised circuits (library engine)
OUT["synth_outer"] = []
for sk, eps in (("pairs9", 1e-6), ("flags4", 1e-6)):
    qo = trotter_v2_circuit(sk, b, with_outer=True); nrot = logical_metrics(qo)["n_rot"]
    synth, info = synthesize(qo, eps); tol = synth_tolerances(nrot, eps)
    v = evaluate(synth, enc, enc.target("UB", None, b), method="physical", gauss=True, **tol)
    r = {"skeleton": sk, "eps": eps, "ok": v.ok, "err": v.op_norm_error, "gauss": v.gauss_residual, "outer_bits_read": v.outer_bits_read, "tol": tol, "n_inputs": v.n_inputs}
    OUT["synth_outer"].append(r); print(r, flush=True)
json.dump(OUT, open("results/spinnet/tester/m3_step_3_6_synth.json", "w"), indent=1, default=str)
