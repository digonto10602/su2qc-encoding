"""Tester script, M3 steps 3.3-3.5 (reports/tests/102).  Independent of the evaluator / sparse engine:
Aer statevector (15-qubit d+a registers on the 47 inner codes, outer register a spectator proven untouched; 16-qubit UE with
outer on all 433; 23-qubit cross-check) against route-B targets (enc.target), route-A targets (exact.operators.target after
gauge_align) and my own diagonal U_E from the labels.  Deterministic (no random numbers except a seeded RNG for the sample)."""
import json, sys, subprocess, time
import numpy as np, scipy.linalg as sl, scipy.sparse as sp
sys.path.insert(0, "src")
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.circuits.spinnet import build_UE, build_UB, build_step
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

# ---- targets
HE_in = np.array([sum(j * (j + 1) for j in lab[0][:4]) for lab in basis.labels])      # own, from route-A labels
HE_all = np.array([sum(j * (j + 1) for j in lab[0]) for lab in basis.labels])
OUT["HE_inner_vs_enc"] = float(np.abs(HE_in - enc.h_electric()).max())
OUT["HE_all_vs_enc"] = float(np.abs(HE_all - enc.h_electric(True)).max())
OUT["HE_inner_vs_popcount_bits0_3"] = float(np.abs(HE_in - 0.75 * np.array([bin(int(c) & 15).count("1") for c in codes433])).max())
HB = enc.h_magnetic(); HEd = np.diag(enc.h_electric())
def UE_t(a, outer=False): return np.diag(np.exp(-1j * a * (HE_all if outer else HE_in)))
def UB_t(b): return sl.expm(-1j * b * HB)
def T1(a, b): return UB_t(b) @ UE_t(a)
def T2(a, b): return UE_t(a / 2) @ UB_t(b) @ UE_t(a / 2)
def TA(kind, a, b, order=1): return targetA(basis, kind, a, b, order=order)

recs = []
def record(name, W, leak, dirty, targets):
    row = {"name": name, "leak": leak, "dirty": dirty, "gauss": gauss_res(W)}
    uni = specnorm(W.conj().T @ W - np.eye(433)); row["unitarity"] = uni
    for tn, V in targets.items():
        e, ph = err_phase(W, V); row[f"err[{tn}]"] = e
    recs.append(row); print(name, {k: (round(v, 3) if isinstance(v, float) and v > 1e-3 else v) for k, v in row.items() if k != "name"}, flush=True)
    return row

# ---- UE
for a in (0.37, 0.91):
    qc = build_UE(a)
    W, lk, dt = matrix433_from_inner(qc, 8) if False else (None, None, None)
    # UE has no ancilla: 8-qubit runs
    V = run_states(qc, [int(c) for c in inner])
    # outer spectator + physical map
    Wm = np.zeros((433, 433), complex)
    pos = {int(c): i for i, c in enumerate(inner)}
    leak = 0.0
    for k, c in enumerate(codes433):
        d, o = int(c) & 0xFF, int(c) >> 8
        vec = V[pos[d]]
        for d2 in np.flatnonzero(np.abs(vec) > 1e-16):
            code2 = int(d2) | (o << 8)
            if code2 in index: Wm[index[code2], k] = vec[d2]
            else: leak = max(leak, abs(vec[d2]))
    row = record(f"UE a={a} (8q, inner runs)", Wm, leak, 0.0, {"routeB": UE_t(a), "routeA": TA("UE", a, None), "own_diag": UE_t(a)})
    # single j=1/2 link phase sign: code 0b0001, link b
    v1 = run_states(qc, [0b0001])[0]; row["phase_code0001"] = [v1[1].real, v1[1].imag]
    row["phase_expected"] = [float(np.cos(0.75 * a)), float(-np.sin(0.75 * a))]
    row["phase_dev"] = float(abs(v1[1] - np.exp(-0.75j * a)))
    # with outer, no outer electric; 16 qubits, all 433 inputs
    qo = build_UE(a, with_outer=True)
    Vo = run_states(qo, [int(c) for c in codes433]); Wo = np.zeros((433, 433), complex); lko = 0.0
    for k in range(433):
        nz = np.flatnonzero(np.abs(Vo[k]) > 1e-16)
        for x in nz:
            if int(x) in index: Wo[index[int(x)], k] = Vo[k][x]
            else: lko = max(lko, abs(Vo[k][x]))
    row = record(f"UE a={a} with_outer (16q, all 433)", Wo, lko, 0.0, {"routeB": UE_t(a), "routeA": TA("UE", a, None), "outerElec_target(should differ)": UE_t(a, True)})
    qe = build_UE(a, with_outer=True, include_outer_electric=True)
    Ve = run_states(qe, [int(c) for c in codes433]); We = np.zeros((433, 433), complex); lke = 0.0
    for k in range(433):
        for x in np.flatnonzero(np.abs(Ve[k]) > 1e-16):
            if int(x) in index: We[index[int(x)], k] = Ve[k][x]
            else: lke = max(lke, abs(Ve[k][x]))
    record(f"UE a={a} with_outer+outer_electric (16q, all 433)", We, lke, 0.0,
           {"routeB_outer": UE_t(a, True), "routeA_outer": TA("UE", a, None, 1) if False else targetA(basis, "UE", a, None, include_outer_electric=True), "inner_only(should differ)": UE_t(a)})
    # outer phase per outer qubit
    dphase = np.angle(np.diag(We) / np.diag(Wo))
    n_out = np.array([bin(int(c) >> 8).count("1") for c in codes433])
    OUT.setdefault("outer_phase_fit", {})[str(a)] = float(np.abs(dphase - np.angle(np.exp(-0.75j * a * n_out))).max())

# ---- structural: outer never touched; with_outer circuit == no-outer circuit with ancilla shift
def gates(qc, shift_anc_from=None):
    out = []
    for i in qc.data:
        qs = [qc.find_bit(q).index for q in i.qubits]
        out.append((i.operation.name, tuple(qs), tuple(round(float(p), 15) for p in i.operation.params)))
    return out
def shifted(qc_no, n=8, by=8):
    res = []
    for nm, qs, pr in gates(qc_no):
        res.append((nm, tuple(q if q < n else q + by for q in qs), pr))
    return res
OUT["structure"] = {}
for nm, (a, b) in {"UB": (None, 0.61), "step1": (0.37, 0.61), "step2": (0.37, 0.61)}.items():
    if nm == "UB": q0, q1 = build_UB(b), build_UB(b, True)
    else: q0, q1 = build_step(a, b, int(nm[-1])), build_step(a, b, int(nm[-1]), True)
    touched = {qc_idx for _, qs, _ in gates(q1) for qc_idx in qs}
    OUT["structure"][nm] = {"outer_touched": sorted(touched & set(range(8, 16))), "same_as_no_outer_with_anc_shift": gates(q1) == shifted(q0),
                            "qregs": [(r.name, r.size) for r in q1.qregs], "n_qubits": q1.num_qubits, "global_phase": float(q1.global_phase)}
print(OUT["structure"])

# ---- UB, steps via 47 inner runs
nominal_and_alt = [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00)]
mats = {}
for b in (0.4, 0.61, 1.0, 2.0):
    W, lk, dt = matrix433_from_inner(build_UB(b))
    mats[("UB", b)] = W
    record(f"UB b={b}", W, lk, dt, {"routeB": UB_t(b), "routeA": TA("UB", None, b), "routeB(-b)": UB_t(-b)})
for order in (1, 2):
    for a, b in nominal_and_alt:
        W, lk, dt = matrix433_from_inner(build_step(a, b, order))
        mats[("step", order, a, b)] = W
        other = T2(a, b) if order == 1 else T1(a, b)
        tgt = {"routeB": (T1 if order == 1 else T2)(a, b), "routeA": TA("step", a, b, order),
               "wrong_order": other, "routeB(-b)": (T1 if order == 1 else T2)(a, -b),
               "reverse_order_product": (UE_t(a) @ UB_t(b)) if order == 1 else (UB_t(b) @ UE_t(a))}
        record(f"step{order} a={a} b={b}", W, lk, dt, tgt)

# ---- route-A gauge_align on the circuit matrices (independent of enc.gauge)
OUT["gauge_align_checks"] = {}
for key in [("UB", 0.61), ("step", 1, 0.37, 0.61), ("step", 2, 0.37, 0.61), ("step", 2, 1.70, 1.00)]:
    W = mats[key]
    VA = TA("UB", None, key[1]) if key[0] == "UB" else TA("step", key[2], key[3], key[1])
    e, ph = err_phase(W, VA)       # ungauged
    VB = (UB_t(key[1]) if key[0] == "UB" else (T1 if key[1] == 1 else T2)(key[2], key[3]))
    e_B, phB = err_phase(W, VB)
    D, res = gauge_align(W / phB, VA)
    OUT["gauge_align_checks"][str(key)] = {"err_vs_routeA_ungauged": e, "err_vs_routeB": e_B, "gauge_align_resid_vs_routeA": res,
                                             "D_is_enc_gauge": bool(D is not None and (np.abs(D.real - enc.gauge).max() < 1e-9 or np.abs(D.real + enc.gauge).max() < 1e-9))}
print(OUT["gauge_align_checks"])

# ---- Trotter scaling: ||U_n - exp(-i(aHE + bHB))|| vs s
OUT["trotter"] = []
for s in (1.0, 0.5, 0.25, 0.125, 0.0625):
    a, b = 0.37 * s, 0.61 * s
    ex = sl.expm(-1j * (a * HEd + b * HB))
    r = {"s": s}
    for order in (1, 2):
        W, _, _ = matrix433_from_inner(build_step(a, b, order))
        r[f"err{order}"] = err_phase(W, ex)[0]
        r[f"err{order}_no_phase_fit"] = specnorm(W - ex)
        # also vs target (the Trotter formula) as sanity
        r[f"err{order}_vs_formula"] = err_phase(W, (T1 if order == 1 else T2)(a, b))[0]
    OUT["trotter"].append(r); print(r, flush=True)
e1 = np.array([r["err1"] for r in OUT["trotter"]]); e2 = np.array([r["err2"] for r in OUT["trotter"]]); ss = np.array([r["s"] for r in OUT["trotter"]])
OUT["trotter_slopes"] = {"order1_loglog": float(np.polyfit(np.log(ss[1:]), np.log(e1[1:]), 1)[0]), "order2_loglog": float(np.polyfit(np.log(ss[1:]), np.log(e2[1:]), 1)[0])}
print(OUT["trotter_slopes"])

# ---- counts, own lowering with qiskit
BASIS = ["cx", "h", "s", "sdg", "t", "tdg", "x", "z", "rz"]
from su2plaq.metrics.logical import logical_metrics, lower
OUT["counts"] = {}
def tcount(low):
    ops = dict(low.count_ops()); nrot = 0; tf = ops.get("t", 0) + ops.get("tdg", 0)
    for i in low.data:
        if i.operation.name == "rz":
            th = float(i.operation.params[0]); kk = th / (np.pi / 4)
            if abs(kk - round(kk)) < 1e-9:
                if round(kk) % 2: tf += 1
            else: nrot += 1
    return ops, nrot, tf
for nm, qc in {"UE": build_UE(0.37), "UE+outer(12 rot)": build_UE(0.37, True, True), "UB": build_UB(0.61), "step1": build_step(0.37, 0.61, 1), "step2": build_step(0.37, 0.61, 2),
               "UB with_outer": build_UB(0.61, True), "step2 with_outer": build_step(0.37, 0.61, 2, True)}.items():
    low = transpile(qc, basis_gates=BASIS + ["p"] if False else BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
    ops, nrot, tf = tcount(low); lm = logical_metrics(qc)
    OUT["counts"][nm] = {"own_ops": {k: int(v) for k, v in ops.items()}, "own_cx": int(ops.get("cx", 0)), "own_nrot": nrot, "own_tfixed": tf, "own_depth": low.depth(),
                         "lib": {k: lm[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits", "ancilla")}, "raw_ops": {k: int(v) for k, v in qc.count_ops().items()},
                         "raw_size": qc.size(), "raw_depth": qc.depth(), "lib_rz_over_beta": [x / 0.61 for x in lm["rz_angles"]]}
    print(nm, OUT["counts"][nm]["own_cx"], nrot, tf, low.depth(), lm["depth"], flush=True)
# depth sensitivity: add a full data-layer to UB
ub = build_UB(0.61); extra = QuantumCircuit(*ub.qregs)
for q in range(8): extra.p(0.1, q)
extra.compose(ub, inplace=True)
low = transpile(extra, basis_gates=BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
OUT["depth_probe_p_on_all_8_data_qubits_then_UB"] = low.depth()
ublow = transpile(ub, basis_gates=BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False)
OUT["UB_depth_own"] = ublow.depth()
# ASAP first layer per qubit in UB, and depth of UB with qubits 0..3 delayed by exactly one layer
def asap(low, delay=None):
    t = {q: 0 for q in range(low.num_qubits)}
    if delay:
        for q in delay: t[q] = 1
    for i in low.data:
        qs = [low.find_bit(q).index for q in i.qubits]; m = max(t[q] for q in qs) + 1
        for q in qs: t[q] = m
    return max(t.values()), t
OUT["UB_asap_depth"] = asap(ublow)[0]
OUT["UB_asap_depth_delay_q0-3_by_1"] = asap(ublow, [0, 1, 2, 3])[0]
OUT["UB_asap_final_time_per_qubit"] = {str(q): v for q, v in asap(ublow)[1].items()}
# step2 end-layer slack: depth(UB then p on q0..3)
tail = QuantumCircuit(*ub.qregs); tail.compose(ub, inplace=True)
for q in range(4): tail.p(0.1, q)
OUT["UB_then_p_q0-3_depth"] = transpile(tail, basis_gates=BASIS, optimization_level=0, seed_transpiler=1, qubits_initially_zero=False).depth()

# ---- angle linearity + skeleton identity
def skel(qc): return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
OUT["skeleton_identical"] = {}
OUT["angles"] = {}
for nm, f in {"UB": lambda a, b: build_UB(b), "step1": lambda a, b: build_step(a, b, 1), "step2": lambda a, b: build_step(a, b, 2)}.items():
    ref = skel(f(0.37, 0.61))
    OUT["skeleton_identical"][nm] = {str((a, b)): skel(f(a, b)) == ref for a, b in nominal_and_alt + [(0.01, 0.02), (3.0, -0.4)]}
from fractions import Fraction
for b in (0.4, 0.61, 1.0, 2.0, 0.23, -0.4):
    qc = build_UB(b); rz = [float(i.operation.params[0]) for i in qc.data if i.operation.name == "rz"]
    OUT["angles"][str(b)] = {"rz_over_beta": [x / b for x in rz], "fractions_meta": qc.metadata["angle_fractions"],
                              "dev_from_fraction": max(abs(x - float(Fraction(s)) * b) for x, s in zip(rz, qc.metadata["angle_fractions"]))}
for a in (0.37, 0.91, 1.7):
    qc = build_UE(a); ps = [float(i.operation.params[0]) for i in qc.data]; OUT["angles"][f"UE_a={a}"] = {"p_over_alpha": [x / a for x in ps]}
    qs = build_step(a, 0.61, 2); ps = [float(i.operation.params[0]) for i in qs.data if i.operation.name == "p"]; OUT["angles"][f"step2_p_a={a}"] = [x / a for x in ps]
OUT["records"] = recs
json.dump(OUT, open(sys.argv[1], "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
print("partial json written", flush=True)
# ---- 23-qubit cross-check: ONE state at a time (128 MB statevector), 20 seeded states per circuit
t0 = time.time()
rng = np.random.default_rng(12345)
for nm, qc, Wref in [("UB b=0.61 with_outer", build_UB(0.61, True), mats[("UB", 0.61)]),
                     ("step1 (0.37,0.61) with_outer", build_step(0.37, 0.61, 1, True), mats[("step", 1, 0.37, 0.61)]),
                     ("step2 (0.37,0.61) with_outer", build_step(0.37, 0.61, 2, True), mats[("step", 2, 0.37, 0.61)])]:
    ks = rng.choice(433, 20, replace=False)
    maxdev = 0.0; dirty = 0.0; leak = 0.0
    for k in ks:
        vec = run_states(qc, [int(codes433[k])], chunk=1)[0]
        col = np.zeros(433, complex)
        for x in np.flatnonzero(np.abs(vec) > 1e-16):
            x = int(x)
            if x >> 16: dirty += abs(vec[x]) ** 2
            elif x in index: col[index[x]] = vec[x]
            else: leak = max(leak, abs(vec[x]))
        maxdev = max(maxdev, float(np.abs(col - Wref[:, k]).max()))
        del vec
    OUT.setdefault("cross23", {})[nm] = {"n_inputs": int(len(ks)), "max_entry_dev_vs_15q_inner_runs": maxdev, "dirty_ancilla_total": float(dirty), "leak": float(leak), "seconds": time.time() - t0}
    print(nm, OUT["cross23"][nm], flush=True)
json.dump(OUT, open(sys.argv[1], "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
print("done")
