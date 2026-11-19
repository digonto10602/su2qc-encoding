"""Fuzzy benchmark worker (tester, reports/benchmarks/304); tasks as report 300 (fresh process each).  BENCH_ROOT selects the source tree.
usage: python w_fuzzy.py <task>; prints RESULT {task, times, rss_mb, out}.  Tasks: build, verify_link, verify_plaquette, verify_step1."""
import sys, os, json, time, resource
ROOT = os.environ.get("BENCH_ROOT", "/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, ROOT + "/src")
task = sys.argv[1]; T = {}; OUT = {}
def timed(name, f, reps=1):
    r = None
    for _ in range(reps):
        t0 = time.perf_counter(); r = f(); T.setdefault(name, []).append(time.perf_counter() - t0)
    return r
alpha, beta, kappa2 = 0.37, 0.61, 0.185
t0 = time.perf_counter()
from su2plaq.circuits import fuzzy as C
from su2plaq.fuzzy import targets as tg
from su2plaq.fuzzy import verify as vf
T["import"] = [time.perf_counter() - t0]
if task == "build":
    qc = timed("build_UB", lambda: C.build_UB(beta), 3); OUT["cx_UB"] = qc.count_ops().get("cx", 0)
    qc = timed("build_step1", lambda: C.build_step(alpha, beta, kappa2=kappa2, order=1), 3); OUT["cx_step1"] = qc.count_ops().get("cx", 0)
elif task == "verify_link":
    V = tg.UE_link(alpha); qc = C.link_UE(alpha)
    v = timed("verify_link", lambda: vf.verify_link(qc, V, tol_err=1e-10), 5); OUT = dict(ok=v.ok, op=v.op_norm_error)
elif task == "verify_plaquette":
    qc = C.build_UB(beta); V = tg.UB_row(beta)
    v = timed("verify_plaquette", lambda: vf.verify_plaquette(qc, V, tol_err=1e-10), 3); OUT = dict(ok=v.ok, op=v.op_norm_error)
elif task == "verify_step1":
    qc = C.build_step(alpha, beta, kappa2=kappa2, order=1)
    r = timed("verify_step_samples", lambda: vf.verify_step_samples(qc, alpha, beta, kappa2, 1, n_random=32, n_phys=8, seed=20261104))
    OUT = {k: r[k] for k in ("err", "gauss", "n_inputs", "leak", "mode") if k in r}
else:
    raise SystemExit("unknown task")
print("RESULT " + json.dumps({"task": task, "times": T, "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, "out": OUT}, default=str), flush=True)
