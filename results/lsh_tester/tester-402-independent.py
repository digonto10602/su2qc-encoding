"""Tester-402 independent verification of M7 steps 7.6 (walk, build_UB) and 7.7 (build_step orders 1, 2).
Own pieces: label -> 24-bit LSH code (from the loop numbers), route-B 6j target expm(-i beta H_B^{6j}) and diagonal U_E
from the labels (no code from su2plaq.lsh / encodings.lsh is used to compute expected numbers), an own sparse gate-walk
simulator (cx, x, h, rccx via Qiskit's RCCXGate matrix, p, rz, s, sdg, t, tdg, z; amplitudes as dicts over 24+7 bit codes),
own gate/CX/T/depth recount (rccx expanded with Qiskit's RCCXGate().definition), own pygridsynth T count.
Run:  PYTHONPATH=src python results/lsh_tester/tester-402-independent.py results/lsh_tester/tester-402-independent.json
(importable as a module: `from tester_402_independent import ...` is not needed; the mutation harness runs this file as a script
with --quick, which only runs sections A, B, E and prints "MUTANT_DETECTED" iff any check fails.)"""
import json, subprocess, sys, time, math
from collections import defaultdict
import numpy as np
import scipy.linalg as sla

QUICK = "--quick" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUTP = args[0] if args else None
SEED = 20261110
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
       "seed": SEED, "checks": []}
NFAIL = [0]


def rec(name, expected, got, tol, ok):
    ok = bool(ok)
    NFAIL[0] += (not ok)
    out["checks"].append({"check": name, "expected": expected, "got": got, "tol": tol, "ok": ok})
    print(("PASS " if ok else "FAIL ") + name, "| expected", expected, "| got", got, "| tol", tol, flush=True)


from qiskit import QuantumCircuit
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator
from su2plaq.exact import spinnet as RB
from su2plaq.circuits.lsh import build_UB, build_step
from su2plaq.lsh import walk as W

t0 = time.time()
labels = RB.labels(jmax=0.5)
assert len(labels) == 433
PN = [(3, 0), (0, 1), (1, 2), (2, 3)]
OUT = [(4, 5), (6, 7), (8, 9), (10, 11)]


def site_bits(j1, j2, J):
    l12, l23, l31 = j1 + j2 - J, j2 + J - j1, J + j1 - j2
    return int(round(l12)) | (int(round(l23)) << 1) | (int(round(l31)) << 2)


def my_code(label):
    j, J = label
    code = 0
    for c in range(4):
        code |= site_bits(j[PN[c][0]], j[PN[c][1]], J[c]) << (3 * c)
        code |= site_bits(j[OUT[c][0]], j[OUT[c][1]], J[c]) << (12 + 3 * c)
    return code


mine = [my_code(l) for l in labels]
c2i = {c: k for k, c in enumerate(mine)}
assert len(c2i) == 433
HB = RB.h_magnetic_phys_6j(labels)
HE_own = np.array([sum(x * (x + 1) for x in j[:4]) for j, _ in labels])


def VB(beta):
    return sla.expm(-1j * beta * HB)


def UE(alpha):
    return np.diag(np.exp(-1j * alpha * HE_own))


def step_target(alpha, beta, order):
    if order == 1:
        return VB(beta) @ UE(alpha)
    return UE(alpha / 2) @ VB(beta) @ UE(alpha / 2)


# ------------------------------------------------------------------ own simulator
RC = Operator(RCCXGate()).data
RC_TAB = {}
for col in range(8):
    rows = np.flatnonzero(np.abs(RC[:, col]) > 1e-12)
    assert len(rows) == 1
    r = int(rows[0])
    RC_TAB[col] = (r, complex(RC[r, col]))          # index = a + 2 b + 4 t (qargs [a, b, t])
ISQ = 1 / math.sqrt(2)


def gates_of(qc):
    g = []
    for inst in qc.data:
        nm = inst.operation.name
        qs = [qc.find_bit(q).index for q in inst.qubits]
        ps = [float(p) for p in inst.operation.params]
        if nm not in ("cx", "x", "h", "rccx", "rz", "p", "s", "sdg", "t", "tdg", "z"):
            raise ValueError("unexpected gate " + nm)
        g.append((nm, qs, ps))
    return g


def sim(gates, code):
    st = {code: 1.0 + 0j}
    for nm, q, p in gates:
        new = {}
        if nm == "cx":
            c, t = 1 << q[0], 1 << q[1]
            for k, v in st.items():
                new[k ^ t if k & c else k] = v
        elif nm == "x":
            t = 1 << q[0]
            for k, v in st.items():
                new[k ^ t] = v
        elif nm == "h":
            b = 1 << q[0]
            acc = defaultdict(complex)
            for k, v in st.items():
                k0 = k & ~b
                acc[k0] += v * ISQ
                acc[k0 | b] += v * ISQ * (-1 if k & b else 1)
            new = {k: v for k, v in acc.items() if abs(v) > 1e-15}
        elif nm == "rccx":
            for k, v in st.items():
                col = ((k >> q[0]) & 1) | (((k >> q[1]) & 1) << 1) | (((k >> q[2]) & 1) << 2)
                row, ph = RC_TAB[col]
                k2 = (k & ~(1 << q[2])) | (((row >> 2) & 1) << q[2])
                new[k2] = v * ph
        else:   # diagonal one-qubit
            for k, v in st.items():
                b = (k >> q[0]) & 1
                if nm == "rz":
                    ph = np.exp(1j * p[0] * (b - 0.5))
                elif nm == "p":
                    ph = np.exp(1j * p[0] * b)
                elif nm == "z":
                    ph = -1 if b else 1
                elif nm == "s":
                    ph = 1j if b else 1
                elif nm == "sdg":
                    ph = -1j if b else 1
                elif nm == "t":
                    ph = np.exp(1j * math.pi / 4) if b else 1
                elif nm == "tdg":
                    ph = np.exp(-1j * math.pi / 4) if b else 1
                new[k] = v * ph
        st = new
    return st


def matrix(qc, n_in=24):
    """433x433 block of the circuit on the physical codes (outer register present), leak/dirty/outer-changed statistics."""
    gates = gates_of(qc)
    M = np.zeros((433, 433), dtype=complex)
    leak_cols = []
    outer_changed = 0.0
    dirty = 0.0
    leak_total = 0.0
    X = defaultdict(lambda: np.zeros(433, dtype=complex))
    for k in range(433):
        st = sim(gates, mine[k])
        for key, v in st.items():
            if key >> 24:
                dirty += abs(v) ** 2
                X[key][k] += v
                continue
            if (key >> 12) != (mine[k] >> 12):
                outer_changed += abs(v) ** 2
            if key in c2i:
                M[c2i[key], k] += v
            else:
                leak_total += abs(v) ** 2
                X[key][k] += v
    Xm = np.array(list(X.values())) if X else np.zeros((0, 433))
    xn = float(np.linalg.norm(Xm, 2)) if len(Xm) else 0.0
    return M, {"dirty": dirty, "outer_changed": outer_changed, "leak_weight": leak_total, "leak_opnorm": xn}


def dist(M, V):
    ph = np.vdot(V.ravel(), M.ravel())
    ph = ph / abs(ph)
    return float(np.linalg.norm(M - ph * V, 2))


def touched(qc):
    return {qc.find_bit(q).index for inst in qc.data for q in inst.qubits}


rng = np.random.default_rng(SEED)

# ------------------------------------------------------------------ A. build_UB
beta_list = [0.4, 0.61, 1.0, 2.0, float(rng.uniform(0.05, 3.0))]
for beta in beta_list:
    qc = build_UB(beta, with_outer=True)
    M, st = matrix(qc)
    V = VB(beta)
    e = dist(M, V)
    tch = touched(qc)
    unit = float(np.linalg.norm(M.conj().T @ M - np.eye(433), 2))
    rec(f"UB beta={beta:.6f}: block err vs expm(-i beta H_B^6j) (433 states, 24 data+outer + 7 anc)", 0, e, 1e-10, e <= 1e-10)
    rec(f"UB beta={beta:.6f}: leak weight / opnorm, dirty ancilla weight, outer-changed weight", 0,
        f"{st['leak_weight']:.2e}/{st['leak_opnorm']:.2e}/{st['dirty']:.2e}/{st['outer_changed']:.2e}", 1e-20,
        st["leak_weight"] <= 1e-20 and st["dirty"] <= 1e-20 and st["outer_changed"] <= 1e-20)
    rec(f"UB beta={beta:.6f}: outer qubits 12..23 untouched by any gate; unitary block", True, f"touched&outer={sorted(tch & set(range(12,24)))}, |M^dM-1|={unit:.1e}", 1e-10,
        not (tch & set(range(12, 24))) and unit <= 1e-10)
    qn = build_UB(beta)
    same = [(a.operation.name, [qn.find_bit(q).index for q in a.qubits]) for a in qn.data]
    relabel = lambda i: i if i < 12 else i - 12
    other = [(a.operation.name, [relabel(qc.find_bit(q).index) for q in a.qubits]) for a in qc.data]
    rec(f"UB beta={beta:.6f}: with/without outer register: identical gate list (after relabelling)", True, same == other, "exact", same == other)

# angles / beta
qc = build_UB(0.61)
angs = [float(i.operation.params[0]) for i in qc.data if i.operation.name == "rz"]
fr = sorted(a / 0.61 for a in angs)
rec("UB(0.61) rz angles / beta (sorted)", [-3.5, -1.0, 1.5, 3.0], [round(x, 12) for x in fr], 1e-12, np.allclose(fr, [-3.5, -1.0, 1.5, 3.0], atol=1e-12))
rec("UB angle linearity: angles(beta=2.0)/2.0 == angles(0.61)/0.61", True, True, 1e-12,
    np.allclose(sorted(float(i.operation.params[0]) / 2.0 for i in build_UB(2.0).data if i.operation.name == "rz"), fr, atol=1e-12))

# ------------------------------------------------------------------ B. build_step
pairs = [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00), (float(rng.uniform(0.1, 3)), float(rng.uniform(0.1, 3)))]
for alpha, beta in pairs:
    for order in (1, 2):
        qc = build_step(alpha, beta, order, with_outer=True)
        M, st = matrix(qc)
        ref = step_target(alpha, beta, order)
        e = dist(M, ref)
        other_order = step_target(alpha, beta, 3 - order)
        swapped = (UE(alpha) @ VB(beta)) if order == 1 else None
        eo = dist(M, other_order)
        em = dist(M, step_target(alpha, -beta, order))
        rec(f"step o{order} (a,b)=({alpha:.4f},{beta:.4f}): err vs {'U_B U_E' if order == 1 else 'U_E(a/2) U_B U_E(a/2)'}", 0, e, 1e-10, e <= 1e-10)
        rec(f"step o{order} ({alpha:.4f},{beta:.4f}): leak/dirty/outer-changed weight", 0,
            f"{st['leak_weight']:.1e}/{st['dirty']:.1e}/{st['outer_changed']:.1e}", 1e-20,
            max(st["leak_weight"], st["dirty"], st["outer_changed"]) <= 1e-20)
        wrong = [("other order target", eo), ("target at -beta", em)]
        if swapped is not None:
            wrong.append(("layer-swapped U_E U_B", dist(M, swapped)))
        rec(f"step o{order} ({alpha:.4f},{beta:.4f}): wrong targets rejected (>1e-3): " + ", ".join(f"{n}={v:.3f}" for n, v in wrong),
            ">1e-3", [round(v, 3) for _, v in wrong], 1e-3, all(v > 1e-3 for _, v in wrong))
        tch = touched(qc)
        rec(f"step o{order} ({alpha:.4f},{beta:.4f}): outer qubits untouched", True, not (tch & set(range(12, 24))), "exact", not (tch & set(range(12, 24))))
        if abs(alpha * beta) < 1e-3:
            continue

# ------------------------------------------------------------------ E. transcoder
inner_codes = sorted({c & 0xFFF for c in mine})
rec("47 distinct inner data codes (own labels)", 47, len(inner_codes), "exact", len(inner_codes) == 47)
lab_by_data = {}
for l, c in zip(labels, mine):
    lab_by_data.setdefault(c & 0xFFF, set()).add(tuple(l[1]) + tuple(l[0][:4]))      # (J0..J3, j_b j_r j_t j_l)
rec("a data code determines (J_c, inner j) uniquely", True, all(len(v) == 1 for v in lab_by_data.values()), "exact", all(len(v) == 1 for v in lab_by_data.values()))
bad = 0
images = set()
gates = [(s_[0], list(s_[1:]), []) for s_ in W.TRANSCODE]
for dc in inner_codes:
    (info,) = lab_by_data[dc]
    J, jn = info[:4], info[4:]                     # J_c; j_b, j_r, j_t, j_l  (n(c) = b, r, t, l)
    exp = 0
    for c in range(4):
        exp |= int(jn[c] == 0.5) << (3 * c)            # wire 3c = [j_n(c) = 1/2]
        exp |= int(J[c] == 1.0) << (3 * c + 1)         # wire 3c+1 = [J_c = 1]
        exp |= int(J[c] == 0.5) << (3 * c + 2)         # wire 3c+2 = [J_c = 1/2]
    (key,) = sim(gates, dc).keys()
    images.add(key)
    bad += key != exp
rec("transcoder (own simulation of W.TRANSCODE) -> wires [j_n=1/2], [J=1], [J=1/2] per site, all 47 inner codes", 0, bad, "exact", bad == 0)
rec("transcoder injective on the 47 inner codes", 47, len(images), "exact", len(images) == 47)
# spin-network 16-bit codes: link bits = wires LINK, corner bits = CBIT; compare with SpinNet's own code_of_label
from su2plaq.encodings.spinnet import code_of_label as sn_code
bad = 0
for l, c in zip(labels, mine):
    (key,) = sim(gates, c & 0xFFF).keys()
    sn = sn_code(l)
    got = sum(((key >> W.LINK[i]) & 1) << i for i in range(4)) | sum(((key >> W.CBIT[i]) & 1) << (4 + i) for i in range(4))
    bad += (got != (sn & 0xFF))
rec("transcoded (LINK, CBIT) wires == SpinNet code_of_label low 8 bits, all 433 labels", 0, bad, "exact", bad == 0)

if QUICK:
    print("FAILED_CHECKS", NFAIL[0])
    sys.exit(1 if NFAIL[0] else 0)

# ------------------------------------------------------------------ C. counts recount from gate lists
RCDEF = RCCXGate().definition
rc_ct = RCDEF.count_ops()


def recount(qc):
    ops = defaultdict(int)
    for inst in qc.data:
        ops[inst.operation.name] += 1
    cx = ops["cx"] + ops["rccx"] * rc_ct["cx"]
    tfix = ops["rccx"] * (rc_ct["t"] + rc_ct["tdg"])
    n_rot = ops["rz"] + ops["p"]
    # expanded circuit for depth
    ex = QuantumCircuit(qc.num_qubits)
    for inst in qc.data:
        nm, qs = inst.operation.name, [qc.find_bit(q).index for q in inst.qubits]
        if nm == "rccx":
            for i2 in RCDEF.data:
                ex.append(i2.operation, [qs[RCDEF.find_bit(q).index] for q in i2.qubits])
        else:
            ex.append(inst.operation, qs)
    return {"cx": cx, "t_fixed": tfix, "n_rot": n_rot, "depth": ex.depth(), "n_touched": len(touched(qc)), "ops": dict(ops)}


from su2plaq.metrics.logical import logical_metrics
rows = {}
for nm, qc in (("UB(0.61)", build_UB(0.61)), ("step o1 (0.37,0.61)", build_step(0.37, 0.61, 1)), ("step o2 (0.37,0.61)", build_step(0.37, 0.61, 2))):
    mine_c = recount(qc)
    lm = logical_metrics(qc)
    rows[nm] = (mine_c, lm)
    rec(f"{nm}: CX recount vs logical_metrics", f"{mine_c['cx']}", lm["cx"], "exact", mine_c["cx"] == lm["cx"])
    rec(f"{nm}: T_fixed recount vs logical_metrics", f"{mine_c['t_fixed']}", lm["t_fixed"], "exact", mine_c["t_fixed"] == lm["t_fixed"])
    rec(f"{nm}: n_rot recount vs logical_metrics", f"{mine_c['n_rot']}", lm["n_rot"], "exact", mine_c["n_rot"] == lm["n_rot"])
    rec(f"{nm}: depth recount vs logical_metrics (logical rz/p = 1 layer)", f"{mine_c['depth']}", lm["depth"], "exact", mine_c["depth"] == lm["depth"])
    rec(f"{nm}: qubits touched / num_qubits / logical qubits", "19/19/19", f"{mine_c['n_touched']}/{qc.num_qubits}/{lm['qubits']}", "exact",
        mine_c["n_touched"] == qc.num_qubits == lm["qubits"] == 19)
rec("UB: CX/n_rot/T_fixed/ancilla builder claim 94/4/88/7", "94/4/88/7", f"{rows['UB(0.61)'][0]['cx']}/{rows['UB(0.61)'][0]['n_rot']}/{rows['UB(0.61)'][0]['t_fixed']}/{rows['UB(0.61)'][1]['ancilla']}", "exact",
    (rows['UB(0.61)'][0]['cx'], rows['UB(0.61)'][0]['n_rot'], rows['UB(0.61)'][0]['t_fixed'], rows['UB(0.61)'][1]['ancilla']) == (94, 4, 88, 7))
rec("step o1/o2 CX 94/94; n_rot 8/12", "94/94/8/12", f"{rows['step o1 (0.37,0.61)'][0]['cx']}/{rows['step o2 (0.37,0.61)'][0]['cx']}/{rows['step o1 (0.37,0.61)'][0]['n_rot']}/{rows['step o2 (0.37,0.61)'][0]['n_rot']}", "exact",
    (rows['step o1 (0.37,0.61)'][0]['cx'], rows['step o2 (0.37,0.61)'][0]['cx'], rows['step o1 (0.37,0.61)'][0]['n_rot'], rows['step o2 (0.37,0.61)'][0]['n_rot']) == (94, 94, 8, 12))
# electric phase angle values
p1 = [i.operation.params[0] for i in build_step(0.37, 0.61, 1).data if i.operation.name == "p"]
p2 = [i.operation.params[0] for i in build_step(0.37, 0.61, 2).data if i.operation.name == "p"]
rec("step o1 p angles = -3 alpha/4 (4x); o2 = -3 alpha/8 (8x)", True, (len(p1), len(p2)), 1e-12,
    len(p1) == 4 and len(p2) == 8 and np.allclose(p1, -0.75 * 0.37) and np.allclose(p2, -0.75 * 0.37 / 2))
# own pygridsynth T count
import mpmath
from pygridsynth.gridsynth import gridsynth_gates


def tcount(theta, eps):
    th = float(theta)
    if abs(th / (math.pi / 4) - round(th / (math.pi / 4))) < 1e-12:
        return abs(round(th / (math.pi / 4))) % 2
    return str(gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps)))).count("T")


from su2plaq.metrics.cliffordt import t_table
for nm, qc in (("UB(0.61)", build_UB(0.61)), ("step o1", build_step(0.37, 0.61, 1)), ("step o2", build_step(0.37, 0.61, 2))):
    mc = recount(qc)
    for eps in (1e-6,):
        rots = [i.operation.params[0] for i in qc.data if i.operation.name in ("rz", "p")]
        tt = mc["t_fixed"] + sum(tcount(a, eps) for a in rots)
        row = [r for r in t_table(qc, (eps,), qiskit=False)][0]
        rec(f"{nm}: T_total(eps=1e-6) own pygridsynth vs t_table", tt, row["t_total"], "exact", tt == row["t_total"])
        out["checks"][-1]["T_total"] = tt

# ------------------------------------------------------------------ D. synthesised circuits at eps = 1e-6
from su2plaq.metrics.cliffordt import synthesize
eps = 1e-6
for nm, make in (("UB(0.61)", lambda: build_UB(0.61, with_outer=True)),
                 ("step o1 (0.37,0.61)", lambda: build_step(0.37, 0.61, 1, with_outer=True)),
                 ("step o2 (0.37,0.61)", lambda: build_step(0.37, 0.61, 2, with_outer=True)),
                 ("step o1 (0.91,0.23)", lambda: build_step(0.91, 0.23, 1, with_outer=True))):
    qc = make()
    syn, info = synthesize(qc, eps)
    t_syn = syn.count_ops().get("t", 0) + syn.count_ops().get("tdg", 0)
    Mm, st = matrix(syn)
    if "UB" in nm:
        ref = VB(0.61)
    else:
        a, b = (0.91, 0.23) if "0.91" in nm else (0.37, 0.61)
        ref = step_target(a, b, 1 if "o1" in nm else 2)
    e = dist(Mm, ref)
    budget = info["n_rot"] * eps + 1e-9
    comb = e + st["leak_opnorm"] + math.sqrt(st["dirty"])
    rec(f"synth {nm}: block err + leak opnorm + sqrt(dirty) <= N_rot eps + 1e-9 (N_rot={info['n_rot']}); ratio to budget", f"<= {budget:.3e}",
        f"{comb:.3e} (block {e:.3e}, leak {st['leak_opnorm']:.2e}, dirty {math.sqrt(st['dirty']):.2e}, outer-changed {st['outer_changed']:.1e}); ratio {comb/budget:.3f}", budget, comb <= budget)
    rec(f"synth {nm}: T in synthesised gate list == t_fixed + own pygridsynth sum", True,
        f"{t_syn} vs {recount(make())['t_fixed'] + sum(tcount(i.operation.params[0], eps) for i in make().data if i.operation.name in ('rz','p'))}", "exact",
        t_syn == recount(make())["t_fixed"] + sum(tcount(i.operation.params[0], eps) for i in make().data if i.operation.name in ("rz", "p")))
    out["checks"][-1]["synth_ratio"] = comb / budget

out["wall_s"] = time.time() - t0
out["n_checks"] = len(out["checks"])
out["n_failed"] = NFAIL[0]
print("CHECKS", out["n_checks"], "FAILED", NFAIL[0], "wall", round(out["wall_s"], 1))
if OUTP:
    json.dump(out, open(OUTP, "w"), indent=1, default=float)
sys.exit(1 if NFAIL[0] else 0)
