"""Tester script, step 3.2 (reports/tests/101). Independent of paulo.py parse/QUBIT_MAP: own regex parse of the gate file,
own 15-qubit circuit, qiskit.quantum_info.Statevector + Aer statevector on the 47 inner codes; walk checked with Statevector
and scipy expm of enc.K_codes.  Deterministic (no random numbers).  Usage: python this.py out.json"""
import json, re, subprocess, sys, hashlib
import numpy as np, scipy.linalg as sl
sys.path.insert(0, "src")
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from su2plaq.encodings.spinnet import SpinNet
out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()}
enc = SpinNet(); codes = enc.inner_codes(); pos = {int(c): i for i, c in enumerate(codes)}
K = enc.K_codes
# ---------------- Part A: own parse of the file
path = "refs/paulo/spin_network_plaquette3.gates.txt"
raw = open(path).read()
out["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
gl = []
for ln in raw.splitlines():
    if not ln.strip() or ln.startswith("#"): continue
    toks = ln.split(None, 1)[1]                      # drop the index
    m = re.match(r"(\w+)(?:\(([-0-9.e]+)\))?\s+(.*)", toks)
    name, ang, rest = m.group(1), m.group(2), m.group(3)
    qs = [int(x) for x in re.findall(r"q\[(\d+)\]", rest)]
    gl.append((name, qs, None if ang is None else float(ang)))
cnt = {}
for g in gl: cnt[g[0]] = cnt.get(g[0], 0) + 1
out["file_counts"] = cnt
touched = sorted({q for g in gl for q in g[1]})
out["file_touched"] = touched
out["file_p_lines"] = [l for l in raw.splitlines() if " p(" in l or "\tp(" in l or re.match(r"\s*\d+\s+p\(", l)]
cmap = {q: i for i, q in enumerate(touched)}   # compress 15 touched qubits -> 0..14 (ascending: q0-3, q12-15, q16-22)
assert len(touched) == 15
qc = QuantumCircuit(15)
for name, qs, ang in gl:
    w = [cmap[q] for q in qs]
    if name == "p": qc.p(ang, w[0])
    elif name == "tdg": qc.tdg(w[0])
    else: getattr(qc, name)(*w)
# data bit k <-> circuit qubit k for k<8 (links 0-3, corners 4-7 = file 12-15); ancillas 8..14
def run_codes(circ, n, cds):
    cols = []
    for c in cds:
        sv = Statevector.from_int(int(c), 2 ** n).evolve(circ)
        cols.append(np.asarray(sv.data))
    return np.array(cols).T
def block(cols, cds):
    M = np.zeros((len(cds), len(cds)), complex); leak = 0.0; dirty = 0.0
    for j in range(cols.shape[1]):
        v = cols[:, j]; mask = np.ones(len(v), bool)
        for c in cds:
            M[pos[int(c)], j] = v[int(c)]; mask[int(c)] = False
        leak = max(leak, float(np.linalg.norm(v[mask])))
        # dirty ancilla: probability weight with any ancilla bit set
        idx = np.arange(len(v)); dirty = max(dirty, float((np.abs(v[idx >> 8 != 0]) ** 2).sum()))
    return M, leak, dirty
cols = run_codes(qc, 15, codes)
M, leak, dirty = block(cols, codes)
out["paulo_leak_amp"] = leak; out["paulo_dirty_anc_prob"] = dirty
out["paulo_M_unitarity"] = float(np.abs(M.conj().T @ M - np.eye(47)).max())
# Aer cross-check on 5 inputs
from qiskit_aer import AerSimulator
sim = AerSimulator(method="statevector"); aerdev = 0.0
for c in codes[[0, 7, 20, 33, 46]]:
    q2 = QuantumCircuit(15); 
    for b in range(15):
        if (int(c) >> b) & 1: q2.x(b)
    q2.compose(qc, inplace=True); q2.save_statevector()
    from qiskit import transpile
    sv = np.asarray(sim.run(transpile(q2, sim), shots=1).result().get_statevector().data)
    aerdev = max(aerdev, float(np.abs(sv - cols[:, pos[int(c)]]).max()))
out["aer_vs_statevector_maxdev"] = aerdev
def opnorm_phase(A, B):
    # min over global phase of ||A - e^{i phi} B||_2 via phase from trace
    t = np.trace(B.conj().T @ A); ph = t / abs(t) if abs(t) > 1e-14 else 1.0
    return float(np.linalg.norm(A - ph * B, 2)), complex(ph)
beta = 0.05
res = {}
for label, b in (("+beta", beta), ("-beta", -beta)):
    V = sl.expm(-1j * b * K)
    e, ph = opnorm_phase(M, V)
    res[label + "_raw_opnorm_err_47"] = e
out.update(res)
# gauge: per bright pair sign
V = sl.expm(-1j * beta * K)
dark = [c for c in map(int, codes) if abs(K[:, pos[c]]).max() < 1e-12]
bright = [c for c in map(int, codes) if c not in dark]
ph = M[pos[dark[0]], pos[dark[0]]] / V[pos[dark[0]], pos[dark[0]]]
out["global_phase_from_dark"] = [ph.real, ph.imag]
pairs = sorted({tuple(sorted((c, c ^ 15))) for c in bright})
signs = {}
for a, b in pairs:
    r = M[pos[b], pos[a]] / (ph * V[pos[b], pos[a]])
    signs[f"{a:08b}/{b:08b}"] = [float(r.real), float(r.imag)]
out["n_dark"], out["n_bright"], out["n_pairs"] = len(dark), len(bright), len(pairs)
out["pair_ratio_M_over_phaseV_offdiag"] = signs
nminus = sum(1 for v in signs.values() if v[0] < 0)
out["n_pairs_minus"] = nminus
# build D: put -1 on the codes with corner bits 0 (the (c>>4)==0 side) of each negative pair
D = np.ones(47)
for (a, b) in pairs:
    if signs[f"{a:08b}/{b:08b}"][0] < 0:
        side = a if (a >> 4) == 0 else b
        D[pos[side]] = -1
out["n_D_minus"] = int((D < 0).sum())
Dm = np.diag(D)
e, _ = opnorm_phase(M, Dm @ V @ Dm)
out["paulo_gauged_opnorm_err_47"] = e
# diag/other blocks: are any other entries nonzero?
Mt = Dm @ V @ Dm * ph
out["paulo_gauged_entrywise_maxdev"] = float(np.abs(M - Mt).max())
# ---------------- 433 level using own matrices
phys = {int(c): k for k, c in enumerate(enc._codes)}
n = len(phys)
W = np.zeros((n, n), complex); badmass = 0.0
for c, k in phys.items():
    data, outer = c & 0xFF, c >> 8
    for d2 in map(int, codes):
        a = M[pos[d2], pos[data]]
        if abs(a) < 1e-15: continue
        c2 = d2 | (outer << 8)
        if c2 in phys: W[phys[c2], k] += a
        else: badmass += abs(a) ** 2
out["433_nonphysical_output_weight"] = badmass
Vg = enc.regauge(enc.target("UB", None, beta), D)
Vraw = enc.target("UB", None, beta)
e, _ = opnorm_phase(W, Vg); out["paulo_433_gauged_opnorm_err"] = e
e, _ = opnorm_phase(W, Vraw); out["paulo_433_raw_opnorm_err"] = e
out["W_unitarity_433"] = float(np.abs(W.conj().T @ W - np.eye(n)).max())
# Gauss: all outputs physical codes => W maps the Gauss subspace to itself; also check with the library evaluator verdict
from su2plaq.circuits.spinnet import paulo_circuit
from su2plaq.evaluate.evaluator import evaluate
qo = paulo_circuit(with_outer=True)
v = evaluate(qo, enc, Vg, method="physical", gauss=True)
out["evaluator_gauged"] = dict(ok=v.ok, err=v.op_norm_error, leak=v.leak_amplitude, gauss=v.gauss_residual, dirty=v.dirty_ancilla, outer_read=v.outer_bits_read, n=v.n_inputs, engine=v.engine, reason=v.reason)
v = evaluate(qo, enc, Vraw, method="physical")
out["evaluator_raw"] = dict(ok=v.ok, err=v.op_norm_error, leak=v.leak_amplitude, gauss=v.gauss_residual, reason=v.reason)
# parse fidelity: gate by gate (own parse vs paulo_circuit)
qc0 = paulo_circuit()
fm = {0: 0, 1: 1, 2: 2, 3: 3, 12: 4, 13: 5, 14: 6, 15: 7}
fm.update({16 + a: 8 + a for a in range(7)})
mism = 0
assert len(qc0.data) == len(gl)
for inst, (name, qs, ang) in zip(qc0.data, gl):
    idx = tuple(qc0.find_bit(q).index for q in inst.qubits)
    if inst.operation.name != name or idx != tuple(fm[q] for q in qs): mism += 1
    if ang is not None and abs(float(inst.operation.params[0]) - ang) > 0: mism += 1
out["paulo_circuit_gate_mismatches_vs_own_parse"] = mism
out["paulo_circuit_ops"] = dict(qc0.count_ops())
from su2plaq.metrics.logical import logical_metrics, lower
out["paulo_logical_metrics"] = {k: (v_ if isinstance(v_, (int, float, str)) else str(v_)) for k, v_ in logical_metrics(qc0).items()}
low = lower(qc0); out["paulo_lowered_ops"] = dict(low.count_ops())
qo_t = {qo.find_bit(q).index for i in qo.data for q in i.qubits}
out["paulo_with_outer_touches_outer"] = bool(qo_t & set(range(8, 16)))
out["paulo_with_outer_qubits"] = qo.num_qubits
out["paulo_global_phase"] = float(qc0.global_phase)
# ---------------- Part B: GENERAL7
from su2plaq.spinnet.walk import GENERAL7, build_walk, coupling_table, solve_angles, angle_fractions
steps, nanc = GENERAL7
table = coupling_table(enc)
out["table_distinct_nonzero_K"] = sorted({round(abs(v), 12) for v in table.values() if v != 0})
w = {}
for b in (0.4, 0.61, 1.0, 2.0):
    q = build_walk(steps, table, b, nanc)
    cols = run_codes(q, 8 + nanc, codes)
    Mw, lk, dy = block(cols, codes)
    Vw = sl.expm(-1j * b * K)
    err47 = float(np.linalg.norm(Mw - Vw, 2))
    Vt = enc.target("UB", None, b)
    ev = evaluate(q, enc, Vt)
    qoo = build_walk(steps, table, b, nanc, with_outer=True)
    evo = evaluate(qoo, enc, Vt, method="physical", gauss=True)
    rz = [float(i.operation.params[0]) for i in q.data if i.operation.name == "rz"]
    w[str(b)] = dict(err47_scipy_expm=err47, leak=lk, dirty=dy, eval_err=ev.op_norm_error, eval_leak=ev.leak_amplitude,
                     eval_dirty=ev.dirty_ancilla, eval_ok=ev.ok, outer_ok=evo.ok, outer_err=evo.op_norm_error, outer_gauss=evo.gauss_residual,
                     outer_read=evo.outer_bits_read, rz=rz, rz_over_beta=[r / b for r in rz])
out["walk"] = w
out["fractions"] = [str(f) for f in angle_fractions(steps, table)]
th1, r1 = solve_angles(steps, table, 1.0)
out["theta_beta1"] = th1.tolist(); out["solve_residual"] = r1
q = build_walk(steps, table, 0.61, nanc)
out["walk_ops"] = dict(q.count_ops()); out["walk_logical"] = {k: (v_ if isinstance(v_, (int, float, str)) else str(v_)) for k, v_ in logical_metrics(q).items()}
out["walk_qubits"] = q.num_qubits
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ("pair_ratio_M_over_phaseV_offdiag", "file_p_lines")}, indent=1, default=str))
