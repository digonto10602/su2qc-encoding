"""Tester 117: independent keys (CX, T@1e-6, depth_CT, qubits) of the round-1 archive entries, skeleton independence and angle linearity,
static import check, outer-register use.  Usage: keys_own.py <root>"""
import sys, json, ast, hashlib, pathlib, math, random
import numpy as np, mpmath
from qiskit import transpile, QuantumCircuit
import pygridsynth
from su2plaq.spinnet import loop; loop.install()
from su2plaq.compress.spec import default_spec
root = pathlib.Path(sys.argv[1]); out = {}
ALLOWED = {"numpy","math","cmath","itertools","functools","collections","fractions","typing","dataclasses","operator","heapq","bisect","qiskit","__future__"}
PROJ = {"su2plaq.compress.oracle","su2plaq.compress.builder","su2plaq.compress.spec"}
FORB = {"open","exec","eval","compile","__import__","input","breakpoint"}
BASIS = ["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"]
def build(path, a, b):
    ns = {"__name__": "prog"}; exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns["build"](default_spec("spinnet","step").with_angles(a,b)).circuit()
def skeleton(qc):
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
def rot_angles(qc):
    low = transpile(qc, basis_gates=BASIS, optimization_level=0)
    return [(i.operation.name, tuple(low.find_bit(q).index for q in i.qubits), float(i.operation.params[0])) for i in low.data if i.operation.name in ("rz","p")], low
def word_T(th, eps=1e-6):
    # exact multiples of pi/4 are free of synthesis (counted via T_fixed rule: rz(k pi/4) = T^k)
    k = th / (math.pi/4)
    if abs(k - round(k)) < 1e-12:
        k = round(k) % 8
        return {0:0,1:1,2:0,3:1,4:0,5:1,6:0,7:1}[k], True, ""
    w = str(pygridsynth.gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps))))
    return w.count("T"), False, w
def depth_ct(low, eps=1e-6):
    q = QuantumCircuit(low.num_qubits)
    EX = {0:"",1:"T",2:"S",3:"ST",4:"SS",5:"SST",6:"SSS",7:"SSST"}
    for i in low.data:
        nm = i.operation.name; qs = [low.find_bit(x).index for x in i.qubits]
        if nm in ("rz","p"):
            th = float(i.operation.params[0]); k = th/(math.pi/4)
            w = EX[round(k)%8] if abs(k-round(k))<1e-12 else str(pygridsynth.gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps))))
            for ch in reversed(w):
                {"H":q.h,"S":q.s,"T":q.t}.get(ch, lambda *_: None)(qs[0]) if ch in "HST" else (q.h(qs[0]),q.s(qs[0]),q.s(qs[0]),q.h(qs[0])) if ch=="X" else None
        else:
            q.append(i.operation, qs)
    return q.depth()
for eid in ["r04-F1-004","r04-F3-004"]:
    ent = json.load(open(root/f"compress/archive/spinnet/entries/{eid}.json")); f = root/ent["program_path"]; src = f.read_text(); r = {}
    r["sha_equal_archive"] = hashlib.sha256(f.read_bytes()).hexdigest() == ent["program_sha256"]
    # static import / forbidden names check
    tree = ast.parse(src); bad = []
    for n in ast.walk(tree):
        names = []
        if isinstance(n, ast.Import): names = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            if n.level: bad.append("relative")
            names = [n.module or ""]
        for nm in names:
            if nm in PROJ: continue
            if nm.split(".")[0] not in ALLOWED: bad.append(nm)
        if isinstance(n, ast.Name) and n.id in FORB: bad.append(n.id)
        if isinstance(n, ast.Attribute) and n.attr in ("system","popen","environ") : bad.append("attr:"+n.attr)
    imports = sorted({(n.module if isinstance(n, ast.ImportFrom) else a.name) for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [None])})
    r["imports"] = imports; r["static_violations"] = bad
    # keys at nominal
    qc = build(f, 0.37, 0.61)
    t0 = transpile(qc, basis_gates=["cx","u"], optimization_level=0)
    cx = t0.count_ops().get("cx", 0)
    rots, low = rot_angles(qc)
    tf = sum(1 for i in low.data if i.operation.name in ("t","tdg"))
    Ts = [word_T(th) for _, _, th in rots]
    t_rot = sum(x[0] for x in Ts)
    # exact pi/4 multiples: T_fixed already counts 't'/'tdg'; rz(k pi/4) with odd k cost 1 T each -> count separately
    n_synth = sum(1 for x in Ts if not x[1]); n_exact_T = sum(x[0] for x in Ts if x[1])
    r.update({"cx_own": cx, "t_fixed_own": tf, "n_rot_own": len(rots), "n_rot_irrational": n_synth, "t_from_exact_pi4_rotations": n_exact_T,
              "t_from_synth": sum(x[0] for x in Ts if not x[1]), "t_total_own": tf + t_rot, "qubits_own": qc.num_qubits,
              "depth_ct_own": depth_ct(low), "key_archive": ent["key"], "metrics_raw": ent["metrics_raw"]})
    # skeleton independence + angle linearity over 8 angle pairs (3 official + 5 seeded random)
    rng = random.Random(20261107)
    pairs = [(0.37,0.61),(0.91,0.23),(1.70,1.00)] + [(round(rng.uniform(0.05,2.0),4), round(rng.uniform(0.05,1.2),4)) for _ in range(5)]
    sk0 = skeleton(qc); same = True; A = []; 
    for (a,b) in pairs:
        q2 = build(f, a, b); same &= skeleton(q2) == sk0
        rs, _ = rot_angles(q2); A.append([x[2] for x in rs])
    A = np.array(A); X = np.array([[a,b,1.0] for a,b in pairs]); worst = 0.0; consts = []
    for j in range(A.shape[1]):
        # angles mod 2pi: unwrap relative to the first-pair prediction is ambiguous; fit on raw values (ok if no branch jumps)
        coef, *_ = np.linalg.lstsq(X, A[:, j], rcond=None)
        res = np.max(np.abs(X @ coef - A[:, j])); worst = max(worst, res); consts.append(coef.tolist())
    r["skeleton_same_8_pairs"] = bool(same); r["linear_fit_worst_residual"] = float(worst)
    r["rot_coeffs_alpha_beta_const_over_pi"] = [[round(c/np.pi,6) for c in cc] for cc in consts]
    r["nonzero_constant_term_rotations"] = int(sum(abs(cc[2]) > 1e-9 for cc in consts))
    # outer register (qubits 8..15) usage: gate names / positions
    use = {}
    for i in qc.data:
        qs = [qc.find_bit(x).index for x in i.qubits]
        for pos, q in enumerate(qs):
            if 8 <= q < 16: use.setdefault((i.operation.name, pos, len(qs)), 0); use[(i.operation.name, pos, len(qs))] += 1
    r["outer_gate_use(name,pos,arity)"] = {str(k): v for k, v in use.items()}
    # lowered: outer qubit as target of any gate?
    tgt = []
    for i in low.data:
        qs = [low.find_bit(x).index for x in i.qubits]; nm = i.operation.name
        if nm == "cx" and 8 <= qs[1] < 16: tgt.append(("cx_target", qs))
        if nm not in ("cx","cz") and any(8 <= q < 16 for q in qs): tgt.append((nm, qs))
    r["outer_touched_beyond_control_in_lowered"] = tgt
    out[eid] = r; print(eid, json.dumps(r, default=str), flush=True)
json.dump(out, open(pathlib.Path(__file__).with_name("keys_own.json"), "w"), indent=1, default=str)
