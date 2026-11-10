"""Tester script, M3 step 3.7 (reports/tests/104).  Independent recomputation of >= 20 numbers in results/spinnet/{UE,UB,step}.json.
Own Aer statevector runs on the COMMITTED .qpy circuits (47 inner-code runs -> 433x433 matrix, outer register a proven spectator by
the 3.3-3.5 report), own numpy targets, own lowering (transpile opt 0) + count_ops, own mpmath/pygridsynth calls (no project cache),
own Qiskit Clifford+T pass-manager call (seed 12345).  Run: PYTHONPATH=src taskset -c 0-9 python results/spinnet/tester/m3_step_3_7_verify.py"""
import json, subprocess, sys, math, collections
import numpy as np, scipy.linalg as sl
from qiskit import QuantumCircuit, qpy, transpile
from qiskit_aer import AerSimulator
from su2plaq.encodings.spinnet import SpinNet

R = "results/spinnet/"
J = {n: json.load(open(f"{R}{n}.json")) for n in ("UE", "UB", "step")}
OUT = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "seeds": {"qiskit_ct": 12345},
       "json_provenance_commit": J["UB"]["provenance"]["git_commit"], "checks": []}
enc = SpinNet(); basis = enc.basis
codes = np.array(enc._codes, dtype=np.int64); index = {int(c): k for k, c in enumerate(codes)}
inner = [int(c) for c in enc.inner_codes()]
sim = AerSimulator(method="statevector", max_parallel_threads=10)
HB = enc.h_magnetic()
HE_in = np.array([sum(j * (j + 1) for j in lab[0][:4]) for lab in basis.labels])      # own, from route-A labels
HE_all = np.array([sum(j * (j + 1) for j in lab[0]) for lab in basis.labels])

def load(n): return qpy.load(open(f"{R}{n}.qpy", "rb"))[0]
def chk(name, expected, got, tol, kind="abs"):
    if kind == "exact": ok = expected == got
    elif kind == "upper": ok = got <= tol
    else: ok = abs(expected - got) <= tol
    OUT["checks"].append({"check": name, "expected": expected, "got": got, "tol": tol, "kind": kind, "ok": bool(ok)})
    print(("PASS " if ok else "FAIL "), name, "expected", expected, "got", got, "tol", tol, flush=True)

def run_states(qc, inputs, chunk=20):
    nq = qc.num_qubits; res = []
    for s0 in range(0, len(inputs), chunk):
        cs = []
        for x in inputs[s0:s0 + chunk]:
            c = QuantumCircuit(nq)
            for b in range(nq):
                if (x >> b) & 1: c.x(b)
            c.compose(qc, inplace=True); c.save_statevector(); cs.append(c)
        t = transpile(cs, sim, optimization_level=0); r = sim.run(t).result()
        res += [np.asarray(r.data(i)["statevector"]) for i in range(len(t))]
    return np.array(res)

def W433(qc, ndata=8):
    nq = qc.num_qubits; V = run_states(qc, inner); pos = {c: i for i, c in enumerate(inner)}
    Vr = V.reshape(len(inner), 1 << (nq - ndata), 256)
    W = np.zeros((433, 433), complex); leak = 0.0; dirty = 0.0
    for k, c in enumerate(codes):
        d, o = int(c) & 0xFF, int(c) >> 8; vec = Vr[pos[d]]
        dirty = max(dirty, float(np.sum(np.abs(vec[1:]) ** 2))); amp = vec[0]; l2 = 0.0
        for d2 in np.flatnonzero(np.abs(amp) > 1e-16):
            c2 = int(d2) | (o << 8)
            if c2 in index: W[index[c2], k] = amp[d2]
            else: l2 += abs(amp[d2]) ** 2
        leak = max(leak, math.sqrt(l2))
    return W, leak, dirty

def err_phase(W, V):
    t = np.trace(V.conj().T @ W); ph = t / abs(t)
    return float(np.linalg.norm(W - ph * V, 2))

UEt = lambda a: np.diag(np.exp(-1j * a * HE_in))
UBt = lambda b: sl.expm(-1j * b * HB)
# ---------------- verdict errors (Aer) vs JSON claims
cases = {"UE": (load("UE"), UEt(0.37), J["UE"]["verification"]),
         "UB": (load("UB"), UBt(0.61), J["UB"]["verification"]),
         "step": (load("step"), UBt(0.61) @ UEt(0.37), J["step"]["verification"]),
         "step_order2": (load("step_order2"), UEt(0.37 / 2) @ UBt(0.61) @ UEt(0.37 / 2), J["step"]["extra"]["order2"]["verification"]),
         "UB_beta_0_05": (load("UB_beta_0_05"), UBt(0.05), J["UB"]["extra"]["comparison"]["ours_beta_0_05"]["verification"]),
         "UB_pairs9": (load("UB_pairs9"), UBt(0.61), J["UB"]["extra"]["comparison"]["spinnet_v2"]["pairs9"]["verification"]),
         "UB_flags4": (load("UB_flags4"), UBt(0.61), J["UB"]["extra"]["comparison"]["spinnet_v2"]["flags4"]["verification"])}
OUT["verify"] = {}
for nm, (qc, V, ver) in cases.items():
    W, leak, dirty = W433(qc)
    e = err_phase(W, V); uni = float(np.linalg.norm(W.conj().T @ W - np.eye(433), 2))
    OUT["verify"][nm] = {"err": e, "leak": leak, "dirty": dirty, "unitarity": uni, "json_err": ver["op_norm_error"]}
    chk(f"{nm}: own Aer error <= 1e-12 (json says {ver['op_norm_error']:.2e}, ok={ver['ok']})", True, e < 1e-12 and ver["ok"], 0, "exact")
    chk(f"{nm}: own leak/dirty/unitarity small", True, leak < 1e-12 and dirty < 1e-12 and uni < 1e-12, 0, "exact")
    chk(f"{nm}: own error vs json error (both < 1e-13..1e-14 scale)", ver["op_norm_error"], e, 5e-14)

# Paulo's file with the recorded gauge: W ~ D V D, D = sign on data code
P = J["UB"]["extra"]["comparison"]["paulo15"]
minus = set(P["gauge_minus_codes"])
Dg = np.array([-1.0 if (int(c) & 0xFF) in minus else 1.0 for c in codes])
Vp = UBt(0.05); Wp, lkp, dtp = W433(load("UB_paulo15"))
e_g = err_phase(Wp, Dg[:, None] * Vp * Dg[None, :]); e_raw = err_phase(Wp, Vp)
chk("paulo15 own error vs D V D at beta=0.05", P["verification"]["op_norm_error"], e_g, 5e-14)
chk("paulo15 ungauged target rejected (json 0.19967)", P["verification_ungauged_route_b_target"]["op_norm_error"], e_raw, 1e-9)
chk("paulo15 expected ungauged error 2 sin(2 beta)=sin(0.1)*2?: 2*sin(0.1)", 2 * math.sin(0.1), e_raw, 2e-3)
chk("paulo15 gauge: 8 minus codes (one per bright pair)", 8, len(minus), 0, "exact")
OUT["verify"]["paulo15"] = {"err_gauged": e_g, "err_raw": e_raw, "leak": lkp, "dirty": dtp}

# ---------------- own lowering + counts
BASIS = ['cx', 'h', 't', 'tdg', 's', 'sdg', 'x', 'z', 'rz']
def lowered(qc): return transpile(qc, basis_gates=BASIS, optimization_level=0)
def counts(qc):
    t = lowered(qc); o = dict(t.count_ops())
    return {"cx": o.get("cx", 0), "t_fixed": o.get("t", 0) + o.get("tdg", 0), "n_rot": o.get("rz", 0), "depth": t.depth(), "qubits": qc.num_qubits,
            "ancilla": qc.num_qubits - 8 - (8 if qc.num_qubits == 16 else 0), "angles": [float(i.operation.params[0]) for i in t.data if i.operation.name == "rz"]}
files = {"UE": ("UE", J["UE"]["metrics"]["logical"]), "UB": ("UB", J["UB"]["metrics"]["logical"]), "step": ("step", J["step"]["metrics"]["logical"]),
         "step_order2": ("step_order2", J["step"]["extra"]["order2"]["metrics"]["logical"]),
         "UE_outer_row": ("UE_outer_row", J["UE"]["extra"]["outer_electric_row"]["metrics"]["logical"]),
         "UB_paulo15": ("UB_paulo15", P["logical"]), "UB_beta_0_05": ("UB_beta_0_05", J["UB"]["extra"]["comparison"]["ours_beta_0_05"]["logical"]),
         "UB_pairs9": ("UB_pairs9", J["UB"]["extra"]["comparison"]["spinnet_v2"]["pairs9"]["logical"]),
         "UB_flags4": ("UB_flags4", J["UB"]["extra"]["comparison"]["spinnet_v2"]["flags4"]["logical"])}
CNT = {}
for nm, (f, lg) in files.items():
    c = counts(load(f)); CNT[nm] = c
    for k in ("cx", "t_fixed", "n_rot", "depth", "qubits", "ancilla"):
        chk(f"{nm}: {k}", lg[k], c[k], 0, "exact")
# paper-style expected numbers from the brief
exp = {"UB_paulo15": (68, 4, 64, 7), "UB_pairs9": (34, 9, 24, 3), "UB_flags4": (44, 4, 48, 3), "UB": (54, 4, 56, 7), "UB_beta_0_05": (54, 4, 56, 7), "UE_outer_row": (0, 12, 0, 0)}
for nm, (cx, rot, tf, anc) in exp.items():
    c = CNT[nm]; chk(f"brief {nm}: (cx,rot,T_fixed,anc)", [cx, rot, tf, anc], [c["cx"], c["n_rot"], c["t_fixed"], c["ancilla"] if nm != "UE_outer_row" else 0], 0, "exact")

# ---------------- T(eps): own pygridsynth calls
import mpmath
from pygridsynth.gridsynth import gridsynth_gates
def is_ct(th):
    r = th / (math.pi / 4); return abs(r - round(r)) < 1e-12
def tcount_angle(th, eps):
    if is_ct(th): return (1 if int(round(th / (math.pi / 4))) % 2 else 0)   # multiple of pi/4: 0 or 1 T (not counted by the project as rot; check below)
    return str(gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps)))).count("T")
def T_total(nm, eps):
    c = CNT[nm]; return c["t_fixed"] + sum(tcount_angle(a, eps) for a in c["angles"] if not is_ct(a)), sum(1 for a in c["angles"] if is_ct(a))
OUT["T"] = {}
for nm, section in (("UB", J["UB"]["metrics"]["t_table"]), ("UE", J["UE"]["metrics"]["t_table"]), ("step", J["step"]["metrics"]["t_table"]),
                    ("UE_outer_row", J["UE"]["extra"]["outer_electric_row"]["metrics"]["t_table"]), ("step_order2", J["step"]["extra"]["order2"]["metrics"]["t_table"])):
    for row in section:
        if row["eps"] in (1e-6, 1e-10, 1e-4, 1e-8):
            t, nct = T_total(nm if nm != "UE" else "UE", row["eps"]); OUT["T"][f"{nm}@{row['eps']}"] = t
            chk(f"T_total {nm} eps={row['eps']:g}", row["t_total"], t, 0, "exact")
            assert nct == 0
for nm, jrow in (("UB_paulo15", P["t_table_pygridsynth"][0]), ("UB_pairs9", J["UB"]["extra"]["comparison"]["spinnet_v2"]["pairs9"]["t_table_pygridsynth"][0]),
                 ("UB_flags4", J["UB"]["extra"]["comparison"]["spinnet_v2"]["flags4"]["t_table_pygridsynth"][0]),
                 ("UB", J["UB"]["extra"]["comparison"]["ours_beta_0_61"]["t_table_pygridsynth"][0]),
                 ("UB_beta_0_05", J["UB"]["extra"]["comparison"]["ours_beta_0_05"]["t_table_pygridsynth"][0])):
    t, nct = T_total(nm, 1e-6); chk(f"T_total {nm} eps=1e-6 (comparison row)", jrow["t_total"], t, 0, "exact")
for nm, v in (("UB_paulo15", 316), ("UB_pairs9", 576), ("UB_flags4", 298), ("UB", 310), ("UB_beta_0_05", 304)):
    chk(f"brief T(1e-6) {nm}", v, T_total(nm, 1e-6)[0], 0, "exact")
chk("brief outer electric row T(1e-6)=768", 768, T_total("UE_outer_row", 1e-6)[0], 0, "exact")
chk("outer electric row synthesised verdict marked not evaluable",
    True, all(r["synth"]["verdict"].get("evaluable") is False for r in J["UE"]["extra"]["outer_electric_row"]["metrics"]["t_table"]), 0, "exact")

# ---------------- Qiskit Clifford+T seed 12345 at 1e-6 (own call, own lowering)
from qiskit.transpiler import generate_preset_clifford_t_pass_manager
def ct(qc):
    pm = generate_preset_clifford_t_pass_manager(basis_gates=["cx", "h", "s", "sdg", "t", "tdg"], optimization_level=3,
        rz_synthesis_config={"rz_synthesis_error": 1e-6, "rz_cache_error": 1e-7}, seed_transpiler=12345, qubits_initially_zero=False)
    o = pm.run(lowered(qc)); ops = dict(o.count_ops()); return {"t": ops.get("t", 0) + ops.get("tdg", 0), "cx": ops.get("cx", 0), "depth": o.depth()}
cmpj = J["UB"]["extra"]["comparison"]
for nm, j in (("UB_paulo15", cmpj["paulo15"]), ("UB", cmpj["ours_beta_0_61"]), ("UB_beta_0_05", cmpj["ours_beta_0_05"]),
              ("UB_pairs9", cmpj["spinnet_v2"]["pairs9"]), ("UB_flags4", cmpj["spinnet_v2"]["flags4"])):
    r = ct(load(nm)); jj = j["qiskit_clifford_t_eps_1e-6"]; OUT.setdefault("CT", {})[nm] = r
    chk(f"Qiskit CT t,cx,depth {nm}", [jj["t"], jj["cx"], jj["depth"]], [r["t"], r["cx"], r["depth"]], 0, "exact")

# ---------------- physics block
Ph = J["UB"]["extra"]["physics"]
chk("n_physical_states", 433, len(basis.labels), 0, "exact")
chk("n physical (json)", 433, Ph["n_physical_states"], 0, "exact")
chk("47 inner codes", 47, len(set(int(c) & 0xFF for c in codes)), 0, "exact")
V3 = enc.inner_target("UB", None, 0.3)   # extract couplings lambda = atan2(-Im V[c,c^15], Re V[c,c]) / beta
lam = {}
for c in inner:
    p = c ^ 15
    if p in inner and p != c:
        i, k = inner.index(c), inner.index(p)
        if abs(V3[i, k]) > 1e-9: lam[c] = math.atan2(-V3[k, i].imag if False else -V3[k, i].imag, V3[i, i].real) / 0.3
bright = sorted(lam); pairs = {min(c, c ^ 15): round(lam[c], 9) for c in bright}
chk("bright codes 16, pairs 8, dark 31", [16, 8, 31], [len(bright), len(pairs), 47 - len(bright)], 0, "exact")
chk("couplings sorted", [-2.0, -0.5] + [1.0] * 6, sorted(pairs.values())[:1] + [x for x in sorted(pairs.values()) if x == -0.5] + [x for x in sorted(pairs.values()) if x == 1.0], 1e-6, "exact") if False else None
vals = sorted(pairs.values()); chk("couplings values (abs) sorted", sorted([-2.0, -0.5] + [1.0] * 6), vals, 0, "exact") if vals == sorted([-2.0, -0.5] + [1.0] * 6) else chk("couplings values", sorted([-2.0, -0.5] + [1.0] * 6), vals, 1e-6)
ev = np.linalg.eigvalsh(HB); hist = collections.Counter(np.round(ev, 6).tolist())
OUT["HB_spectrum"] = {str(k): v for k, v in sorted(hist.items())}
chk("H_B spectrum multiplicities 16/96/16/177/16/96/16", [16, 96, 16, 177, 16, 96, 16], [hist[k] for k in sorted(hist)], 0, "exact")
chk("gauge minus count 64 (enc.gauge)", 64, int((enc.gauge < 0).sum()), 0, "exact")
pat = collections.Counter(int(c) >> 8 for c in codes); h = collections.Counter(pat.values())
chk("outer patterns 128", 128, len(pat), 0, "exact"); chk("outer pattern dims 2..17 hist", {2: 41, 3: 52, 4: 8, 5: 22, 9: 4, 17: 1}, dict(sorted(h.items())), 0, "exact")
chk("outer-pattern dims min/max", [2, 17], [min(pat.values()) if 0 not in pat else min(v for k, v in pat.items() if k != 0), max(pat.values())], 0, "exact")
chk("json physics histogram matches own", {str(k): v for k, v in sorted(h.items())}, Ph["states_per_outer_pattern_histogram"], 0, "exact")
json.dump(OUT, open(R + "tester/m3_step_3_7.json", "w"), indent=1, default=lambda o: o if not isinstance(o, np.generic) else o.item())
nf = sum(not c["ok"] for c in OUT["checks"]); print("checks", len(OUT["checks"]), "failed", nf)
