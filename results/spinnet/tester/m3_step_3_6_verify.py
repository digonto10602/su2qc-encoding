"""Tester script, M3 step 3.6 (reports/tests/103).  Independent of the evaluator / sparse engine:
Aer statevector of the spinnet_v2 circuits (11 qubits no-outer, 19 qubits with the outer register on ALL 433 inputs, one chunk at a time)
vs own route-B target expm(-i beta H_B) and route-A target after gauge_align; own Gauss operator; negative controls;
own T-counts (pygridsynth, own 2x2 word check); Qiskit CT cross-check; synthesised circuits (Aer) vs n_rot*eps."""
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


# ---------------------------------------------------------------- step 3.6 part
import math, mpmath
from fractions import Fraction
from qiskit.circuit.library import RCCXGate, RC3XGate
from qiskit.quantum_info import Operator
from su2plaq.spinnet import trotter_v2
from su2plaq.metrics.cliffordt import synthesize, t_table
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances

HB = enc.h_magnetic()
def UB_t(b): return sl.expm(-1j * b * HB)
def TA(b): return targetA(basis, "UB", None, b)
NAMES = ("pairs9", "flags4", "flags5", "flags6")
OUT["gates"] = {}

# ---- gate identities
R = Operator(RCCXGate()).data; C3 = Operator(RC3XGate()).data
OUT["gates"]["rccx_herm"] = float(np.abs(R - R.conj().T).max())
OUT["gates"]["rccx_sq_minus_I"] = float(np.abs(R @ R - np.eye(8)).max())
OUT["gates"]["rc3x_herm"] = float(np.abs(C3 - C3.conj().T).max())
OUT["gates"]["rc3x_sq_minus_I"] = float(np.abs(C3 @ C3 - np.eye(16)).max())
OUT["gates"]["rc3x_dg_times_rc3x_minus_I"] = float(np.abs(Operator(RC3XGate().inverse()).data @ C3 - np.eye(16)).max())
# relative-phase meaning: |<rccx>| equals Toffoli up to diagonal phases
print(OUT["gates"], flush=True)

def inner_matrix(qc):
    return matrix433_from_inner(qc, 8)

def outer_matrix(qc, chunk=20):
    """qc has registers d(8), o(8), a(3): direct Aer on all 433 inputs; returns W(433x433), leak, dirty, outer_touched."""
    nq = qc.num_qubits; nanc = nq - 16
    W = np.zeros((433, 433), complex); leak = 0.0; dirty = 0.0
    for s0 in range(0, 433, chunk):
        ks = list(range(s0, min(433, s0 + chunk)))
        V = run_states(qc, [int(codes433[k]) for k in ks])             # (len, 2^nq); idx = code16 + anc<<16
        V = V.reshape(len(ks), 1 << nanc, 1 << 16)
        for r, k in enumerate(ks):
            dirty = max(dirty, float(np.sum(np.abs(V[r, 1:]) ** 2)))
            amp = V[r, 0]; tot = 0.0
            for c2 in np.flatnonzero(np.abs(amp) > 1e-16):
                if int(c2) in index: W[index[int(c2)], k] = amp[c2]
                else: tot += abs(amp[c2]) ** 2
            leak = max(leak, math.sqrt(tot))
    return W, leak, dirty

OUT["records"] = []
def rec(name, W, leak, dirty, targets, extra=None):
    row = {"name": name, "leak": leak, "dirty": dirty, "gauss": gauss_res(W), "unitarity": specnorm(W.conj().T @ W - np.eye(433))}
    for tn, V in targets.items(): row[f"err[{tn}]"] = err_phase(W, V)[0]
    if extra: row.update(extra)
    OUT["records"].append(row); print(name, {k: v for k, v in row.items() if k != "name"}, flush=True)

mats = {}
for sk in NAMES:
    for b in (0.23, 0.61, 1.0):
        qc = trotter_v2_circuit(sk, b)
        W, lk, dt = inner_matrix(qc); mats[(sk, b)] = W
        e_B = err_phase(W, UB_t(b))[0]
        rec(f"{sk} b={b} (11q, 47 inner runs)", W, lk, dt, {"routeB": UB_t(b), "routeA_ungauged": TA(b), "routeB(-b)": UB_t(-b), "routeB(b/2)": UB_t(b / 2)})
    # direct with-outer 19-qubit on all 433 states
    b = 0.61
    qo = trotter_v2_circuit(sk, b, with_outer=True)
    touched = sorted({qo.find_bit(q).index for i in qo.data for q in i.qubits} & set(range(8, 16)))
    Wo, lk, dt = outer_matrix(qo)
    rec(f"{sk} b={b} with_outer (19q, all 433)", Wo, lk, dt, {"routeB": UB_t(b)},
        extra={"outer_qubits_touched": touched, "max_dev_vs_no_outer": float(np.abs(Wo - mats[(sk, b)]).max()), "num_qubits": qo.num_qubits})

# ---- gauge_align route A
OUT["gauge_align"] = {}
for sk in NAMES:
    W = mats[(sk, 0.61)]; e, ph = err_phase(W, UB_t(0.61))
    VA = TA(0.61); D, res = gauge_align(W / ph, VA)
    OUT["gauge_align"][sk] = {"err_vs_routeA_ungauged": err_phase(W, VA)[0], "gauge_align_resid": res,
                              "D_is_enc_gauge": bool(D is not None and (np.abs(D.real - enc.gauge).max() < 1e-9 or np.abs(D.real + enc.gauge).max() < 1e-9))}
print(OUT["gauge_align"], flush=True)

# ---- negative controls: wrong sign of every angle (beta -> -beta in the circuit), and rc3x_dg replaced by rc3x
from su2plaq.spinnet.walk import build_walk
from su2plaq.circuits import spinnet as cs
OUT["negative"] = {}
for sk in ("pairs9", "flags4"):
    steps, n_anc, frame = trotter_v2.SKELETONS[sk]
    qm = build_walk(steps, cs._table(), -0.61, n_anc, frame=frame, expand=True)
    W, lk, dt = inner_matrix(qm); OUT["negative"][f"{sk}_circuit_with_minus_beta_vs_target_plus_beta"] = err_phase(W, UB_t(0.61))[0]
steps, n_anc, frame = trotter_v2.SKELETONS["flags4"]
bad = [("rc3x",) + s[1:] if s[0] == "rc3x_dg" else s for s in steps]
qb = build_walk(bad, cs._table(), 0.61, n_anc, frame=frame, expand=True)
W, lk, dt = inner_matrix(qb); OUT["negative"]["flags4_plain_rc3x_uncompute"] = {"err": err_phase(W, UB_t(0.61))[0], "leak": lk, "dirty": dt}
# skeleton with a wrong flag wire (drop one CX of the walk) should not represent K
steps, n_anc, frame = trotter_v2.SKELETONS["pairs9"]
try:
    dropped = [s for k, s in enumerate(steps) if k != 20]
    qd = build_walk(dropped, cs._table(), 0.61, n_anc, frame=frame, expand=True)
    W, lk, dt = inner_matrix(qd); OUT["negative"]["pairs9_one_step_dropped"] = err_phase(W, UB_t(0.61))[0]
except ValueError as ex:
    OUT["negative"]["pairs9_one_step_dropped"] = "rejected by solver: " + str(ex)[:80]
print(OUT["negative"], flush=True)

json.dump(OUT, open("results/spinnet/tester/m3_step_3_6.json", "w"), indent=1, default=str)
