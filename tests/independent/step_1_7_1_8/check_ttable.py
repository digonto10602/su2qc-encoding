"""Tester script (not collected): M1 step 1.7 T tables, synth->evaluate, error_measured_sum vs own 2x2 computation.
Usage: python check_ttable.py KIND [ORDER]   (KIND in UE UB step); writes results/m1_step_1_7_<tag>.json"""
import sys, json, time, subprocess, math, warnings
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
import mpmath
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_step, build_UE, build_UB
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.metrics.logical import logical_metrics, lower
from su2plaq.metrics.cliffordt import synthesize, t_table

kind = sys.argv[1]; order = int(sys.argv[2]) if len(sys.argv) > 2 else 1
a, b = 0.37, 0.61
qc = {"UE": lambda: build_UE(a), "UB": lambda: build_UB(b), "step": lambda: build_step(a, b, order=order)}[kind]()
tag = kind if kind != "step" else f"step{order}"
enc = TwelveQubit()
V = enc.target("step", a, b, order=order) if kind == "step" else enc.target(kind, a, b)
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
lm = logical_metrics(qc)
rows = t_table(qc, EPS)
low = lower(qc)
angles = [float(i.operation.params[0]) for i in low.data if i.operation.name == "rz"]

# --- own 2x2 computation (pygridsynth called directly; own matrices)
from pygridsynth.gridsynth import gridsynth_gates
H = np.array([[1, 1], [1, -1]]) / math.sqrt(2); S = np.diag([1, 1j]); T = np.diag([1, np.exp(1j * math.pi / 4)])
X = np.array([[0, 1], [1, 0]]); W = np.exp(1j * math.pi / 4) * np.eye(2)
M = dict(H=H, S=S, T=T, X=X, W=W)
def own_err(theta, eps):
    w = str(gridsynth_gates(theta=mpmath.mpf(repr(theta)), epsilon=mpmath.mpf(repr(eps))))
    U = np.eye(2, dtype=complex)
    for ch in w: U = U @ M[ch]
    R = np.diag([np.exp(-0.5j * theta), np.exp(0.5j * theta)])
    # distance up to a phase: min over phi of ||U - e^{i phi} R||_2 ; solve by 1-D scan + refine (independent of project formula)
    from scipy.optimize import minimize_scalar
    f = lambda p: np.linalg.norm(U - np.exp(1j * p) * R, 2)
    grid = np.linspace(-np.pi, np.pi, 721); v = [f(p) for p in grid]; p0 = grid[int(np.argmin(v))]
    r = minimize_scalar(f, bounds=(p0 - 0.01, p0 + 0.01), method="bounded", options=dict(xatol=1e-14))
    return float(r.fun), w.count("T")

out = dict(kind=kind, order=order if kind == "step" else None, alpha=a, beta=b,
           commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted",
           n_rot=lm["n_rot"], t_fixed=lm["t_fixed"], rows=[])
for r in rows:
    eps = r["eps"]
    t0 = time.time()
    synth, info = synthesize(qc, eps)
    ts = time.time() - t0
    tol = synth_tolerances(lm["n_rot"], eps)
    t0 = time.time()
    v = evaluate(synth, enc, V, **tol)
    te = time.time() - t0
    nonexact = [th for th in angles if abs(th / (math.pi / 4) - round(th / (math.pi / 4))) > 1e-12]
    errs_t = [own_err(th, eps) for th in nonexact]
    own_sum = sum(e for e, _ in errs_t); own_T = sum(t for _, t in errs_t)
    per = [p for p in info["per_rotation"] if not p["exact"]]
    t_in_circ = synth.count_ops().get("t", 0) + synth.count_ops().get("tdg", 0)
    row = dict(eps=eps, T_total_table=r["t_total"], t_qiskit=r["t_qiskit"], t_est=r["t_est"], t_rot_py=r["t_rot_pygridsynth"],
               T_in_synth_circuit=t_in_circ, T_own_gridsynth=own_T,
               n_rot=info["n_rot"], error_measured_sum=info["error_measured_sum"], own_error_sum=own_sum,
               sum_of_per_rotation=sum(p["error"] for p in per), error_bound_sum=info["error_bound_sum"], max_single=max(p["error"] for p in per),
               tol_err=tol["tol_err"], ok=v.ok, reason=v.reason, op_norm_error=v.op_norm_error, block_error=v.block_error,
               leak_amplitude=v.leak_amplitude, dropped_total=v.dropped_total, max_dropped_l2=v.extra.get("max_dropped_l2"),
               gauss=v.gauss_residual, certified=v.certified, engine=v.engine, eval_sec=te, synth_sec=ts, cx_synth=synth.count_ops().get("cx", 0))
    out["rows"].append(row)
    print(json.dumps(row), flush=True)
json.dump(out, open(f"results/m1_step_1_7_ttable_{tag}.json", "w"), indent=1)
