"""Tester 205: T-count rows of every results JSON; independent pygridsynth for UE (all eps) and UB/step (eps 1e-4,1e-6)
from rz angles of an independent Qiskit lowering of the loaded .qpy; band, monotonicity, 10 % Qiskit CT, synth verdicts."""
import json, pathlib, math, subprocess, sys
import numpy as np, mpmath
from qiskit import qpy, transpile
from pygridsynth.gridsynth import gridsynth_gates
sys.path.insert(0, "."); from tests.acceptance._api import ross_selinger_band
R = pathlib.Path("results/rishon"); EPS = [1e-4,1e-6,1e-8,1e-10]
out = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), "files": {}}
BASIS=["cx","h","s","sdg","t","tdg","x","z","rz"]
def tcount(theta, eps):
    th = float(theta) % (2*math.pi)
    if abs(th/(math.pi/4) - round(th/(math.pi/4))) < 1e-12:  # Clifford+T angle: exact, T iff odd multiple of pi/4
        return 1 if round(th/(math.pi/4)) % 2 else 0
    return str(gridsynth_gates(theta=mpmath.mpf(repr(float(theta))), epsilon=mpmath.mpf(repr(eps)))).count("T")
allok = True
for k in ["UE","UE_outer_row","UB","step","step_order2"]:
    d = json.load(open(R/f"{k}.json")); rows = d["metrics"]["t_table"]; rec = {"rows": []}
    qc = qpy.load(open(d["files"]["qpy"],"rb"))[0]
    low = transpile(qc, basis_gates=BASIS, optimization_level=0, seed_transpiler=1)
    angles = [float(i.operation.params[0]) for i in low.data if i.operation.name=="rz"]
    nrot = len(angles); tf = sum(1 for i in low.data if i.operation.name in ("t","tdg"))
    prev = None
    for r in rows:
        e = r["eps"]; lo, hi = ross_selinger_band(e); n=r["n_rot"]
        s = r["synth"]; v = s["verdict"]; tolx = n*e+1e-9
        c = {"eps": e, "t_total": r["t_total"], "t_total_eq": r["t_total"]==r["t_fixed"]+r["t_rot_pygridsynth"],
             "t_fixed_indep": tf==r["t_fixed"], "n_rot_indep": nrot==n,
             "band": n*lo <= r["t_rot_pygridsynth"] <= n*hi, "t_per_rot": r["t_rot_pygridsynth"]/n if n else None,
             "t_est_ok": abs(r["t_est"]-(r["t_fixed"]+3*n*math.log2(1/e)))<=1e-6,
             "qiskit_ratio": r["t_qiskit"]/r["t_total"] if r["t_total"] else None,
             "qiskit_within_10pct": abs(r["t_qiskit"]-r["t_total"])<=0.10*max(r["t_total"],1),
             "cx_qiskit_ok": r["cx_qiskit"] <= 1.1*d["metrics"]["logical"]["cx"]+2,
             "monotone": prev is None or r["t_total"]>prev, "t_matches_table": s["t_matches_table"],
             "synth_n_rot": s["n_rot"]==n, "bound_sum_le": s["error_bound_sum"] <= n*e*(1+1e-12), "meas_le_bound": s["error_measured_sum"] <= s["error_bound_sum"]}
        prev = r["t_total"]
        if k=="UE_outer_row":
            err = v["max_error"]; c.update(synth_err=err, synth_tol=v["tolerances"]["tol_err"], sampled=v["sampled"], certified=v["certified"], ok=v["ok"])
            c["err_le_tol"] = err <= tolx; c["tol_is_nrot_eps"] = abs(v["tolerances"]["tol_err"]-tolx)<1e-15
        else:
            c.update(synth_op=v["op_norm_error"], synth_gauss=v["gauss_residual"], synth_leak=v["leak_amplitude"], synth_tol=v["tolerances"]["tol_err"],
                     ok=v["ok"], certified=v["certified"], gauss_states=v["gauss_states"], outer_bits_read=v["outer_bits_read"])
            c["err_le_tol"] = v["op_norm_error"] <= tolx and v["gauss_residual"] <= tolx and v["leak_amplitude"] <= tolx
            c["tol_is_nrot_eps"] = abs(v["tolerances"]["tol_err"]-tolx)<1e-15 and abs(v["tolerances"]["tol_gauss"]-tolx)<1e-15
            c["op_norm_decomposition_ok"] = v["op_norm_error"] <= v["block_error"]+v["dropped_total"]+v["leak_amplitude"]+1e-15
        # independent pygridsynth sum
        if k=="UE" or (k in ("UB","step","step_order2","UE_outer_row") and e in (1e-4,1e-6)):
            ind = sum(tcount(a,e) for a in angles); c["indep_t_rot"]=ind; c["indep_t_rot_eq"]= ind==r["t_rot_pygridsynth"]
        c["pass"] = all(x for kk,x in c.items() if isinstance(x,bool) and not (k=="UE_outer_row" and kk=="certified")) and (k!="UE_outer_row" or (c["certified"] is False and c["sampled"] is True))
        allok &= c["pass"]; rec["rows"].append(c)
    out["files"][k]=rec
    print(k, [(c["eps"], c["t_total"], c["pass"], round(c["qiskit_ratio"],3), c.get("indep_t_rot_eq")) for c in rec["rows"]], flush=True)
out["all_pass"]=allok; print("ALL", allok)
json.dump(out, open(R/"tester-205-ttable.json","w"), indent=1, default=str)
