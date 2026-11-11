"""Tester 118: shipped artifacts of step 4.7. (a) load results/spinnet/m4-headline-step.qpy and the .qasm3, run each by Aer on all 433 codes at (0.37,0.61)
against my own target (aer_verify helpers); (b) sha256 in m4-compressed.json == file sha; (c) independent T(eps), CX, N_rot, T_fixed, T_avg of the headline, CX/T of general (r00-seed-000)
and pairs9 (r00-seed-001) with own pygridsynth; (d) savings."""
import sys, json, math, hashlib, pathlib, numpy as np, mpmath, pygridsynth
from qiskit import qpy, transpile
import aer_verify as AV
from su2plaq.compress.spec import default_spec
root = pathlib.Path(".")
M4 = json.load(open(root/"results/spinnet/m4-compressed.json")); out = {}
def err_of(qc, a, b):
    cols = AV.run(qc); V = AV.target(a, b); M = np.zeros((433, 433), complex); anc = leak = 0.0
    for k, (nz, amp) in enumerate(cols):
        for i, z in zip(nz, amp):
            w = abs(z)**2
            if int(i) >> 16: anc += w; continue
            j = AV.index.get(int(i))
            if j is None: leak += w
            else: M[j, k] = z
    ov = np.trace(V.conj().T @ M); ph = ov/abs(ov)
    return {"block_err_2norm": float(np.linalg.norm(M - ph*V, 2)), "ancilla_weight": anc, "leak_weight": leak, "n_qubits": qc.num_qubits}
for kind in ("qpy", "qasm3"):
    p = root/M4["files"][kind]; out[f"sha_{kind}"] = hashlib.sha256(p.read_bytes()).hexdigest()
out["json_sha_equals_qpy_file"] = out["sha_qpy"] == M4["files"]["sha256"]
with open(root/M4["files"]["qpy"], "rb") as fh: qc = qpy.load(fh)[0]
out["qpy"] = err_of(qc, 0.37, 0.61); print("qpy", out["qpy"], flush=True)
try:
    from qiskit import qasm3
    qc3 = qasm3.loads((root/M4["files"]["qasm3"]).read_text()); out["qasm3"] = err_of(qc3, 0.37, 0.61); print("qasm3", out["qasm3"], flush=True)
except Exception as e: out["qasm3"] = f"not run: {type(e).__name__}: {e}"[:200]; print(out["qasm3"])
# (c)
BASIS = ["cx","h","s","sdg","t","tdg","rz","p","x","z","cz"]
def build(path, a, b):
    ns = {"__name__": "prog"}; exec(compile((root/path).read_text(), path, "exec"), ns); return ns["build"](default_spec("spinnet", "step").with_angles(a, b)).circuit()
EX = {0:"",1:"T",2:"S",3:"ST",4:"SS",5:"SST",6:"SSS",7:"SSST"}
def Tcount(th, eps):
    k = th/(math.pi/4)
    if abs(k-round(k)) < 1e-12: return [0,1,0,1,0,1,0,1][round(k) % 8]
    return str(pygridsynth.gridsynth_gates(mpmath.mpf(repr(th)), mpmath.mpf(repr(eps)))).count("T")
def metrics(path, a, b, epss):
    q = build(path, a, b); low = transpile(q, basis_gates=BASIS, optimization_level=0)
    cx = sum(1 for i in transpile(q, basis_gates=["cx","u"], optimization_level=0).data if i.operation.name == "cx")
    tf = sum(1 for i in low.data if i.operation.name in ("t","tdg")); rots = [float(i.operation.params[0]) for i in low.data if i.operation.name in ("rz","p")]
    return {"cx": cx, "t_fixed": tf, "n_rot": len(rots), "qubits": q.num_qubits, **{f"T@{e:g}": tf + sum(Tcount(t, e) for t in rots) for e in epss}}
hp = M4["extra"]["headline"]["program_path"]
out["headline_nominal"] = metrics(hp, 0.37, 0.61, (1e-4, 1e-6, 1e-8, 1e-10)); print(out["headline_nominal"], flush=True)
out["claimed_t_table"] = [(r["eps"], r["t_total"]) for r in M4["metrics"]["t_table"]]; out["claimed_logical"] = M4["metrics"]["logical"]
pairs = M4["extra"]["angle_set"]["pairs"]; Ts = [metrics(hp, a, b, (1e-6,))["T@1e-06"] for a, b in pairs]; out["T_avg_own"] = sum(Ts)/len(Ts); out["T_sum_own"] = sum(Ts)
rows = {r["row"]: r for r in M4["extra"]["before_after"]}
for nm in ("general", "spinnet_v2_pairs9", "best_family_F2", "best_family_F3", "global_best"):
    r = rows[nm]; m = metrics(r["program_path"], 0.37, 0.61, (1e-6, 1e-10)); out[f"row_{nm}"] = {"entry": r["entry"], "own": m, "claimed": {k: r.get(k) for k in ("cx", "t_fixed", "n_rot", "qubits")}}; print(nm, out[f"row_{nm}"], flush=True)
json.dump(out, open("results/spinnet/tester/4_6_r5/artifacts_check.json", "w"), indent=1, default=str)
