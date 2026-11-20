"""LSH M8 benchmark worker (tester, reports/benchmarks/306).  One process, one program.
usage: w_eval.py <mode> <program> <nrep> [cold]
modes: eval    1 warm-up + nrep timed `evaluate_program(path, spec, "full")`, then nrep timed builds (sandbox subprocess, 3 specs),
               nrep `evaluate_circuit` (full: nominal + 2 alternate angle pairs) and nrep verdict-level `evaluate` (nominal, as in the M7 tasks)
       robust  1 warm-up + nrep timed `robust_metrics("lsh","step",path)` (21 builds + 20 measured metrics)
`cold`: su2plaq.compress.synth.CACHE_DIR is pointed at a fresh empty scratch directory (cold pygridsynth cache) and NO warm-up is done
(the first call is the cold one; the later calls are then warm in the fresh directory).
Prints one line RESULT {json}.  Nothing under the repository is written except (warm mode) pygridsynth cache entries (gitignored)."""
import sys, os, json, time, resource, pathlib, tempfile, hashlib
ROOT = str(pathlib.Path(__file__).resolve().parents[4])
sys.path.insert(0, ROOT + "/src")
mode, prog, nrep = sys.argv[1], sys.argv[2], int(sys.argv[3]); cold = len(sys.argv) > 4 and sys.argv[4] == "cold"
from su2plaq.compress import evaluate as E
from su2plaq.compress import synth as S
from su2plaq.compress.spec import default_spec, get_encoding
if cold:
    S.CACHE_DIR = pathlib.Path(tempfile.mkdtemp(prefix="gs_cold_", dir=os.environ.get("BENCH_SCR", None)))
sp = default_spec("lsh", "step")
path = pathlib.Path(prog)
out = {"mode": mode, "program": prog, "cold": cold, "program_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
def tm(f):
    t = time.perf_counter(); r = f(); return time.perf_counter() - t, r
if mode == "eval":
    calls = []
    n_first = 0 if cold else 1
    for i in range(n_first + nrep):
        dt, r = tm(lambda: E.evaluate_program(path, sp, "full", cache=False))
        calls.append(dt)
        if not r.valid: raise SystemExit(f"invalid: {r.reason}")
    m = r.metrics
    out.update(calls=calls, n_warmup=n_first, valid=r.valid, reason=r.reason, cx=m["cx"], t_eps=m["t_eps"], depth_ct=m["depth_ct"], qubits=m["qubits"],
               n_rot=m["n_rot"], t_fixed=m["t_fixed"], depth=m["depth"], wall_s_last=r.wall_s)
    src = path.read_bytes(); specs = [sp] + [sp.with_angles(a, b) for a, b in sp.alt_angles]
    out["build_s"] = []
    for i in range(nrep):
        dt, (circs, _) = tm(lambda: E._build_in_subprocess(src, specs, E.BUILD_TIMEOUT_S)); out["build_s"].append(dt)
    out["evaluate_circuit_s"] = []
    for i in range(nrep):
        dt, r2 = tm(lambda: E.evaluate_circuit(circs[0], sp, "full", alt_circuits=circs[1:], program_sha256=out["program_sha256"])); out["evaluate_circuit_s"].append(dt)
    from su2plaq.evaluate.evaluator import evaluate
    enc = get_encoding("lsh"); V = enc.target("step", sp.alpha, sp.beta, 1)
    out["verdict_evaluate_s"] = []
    for i in range(nrep):
        dt, v = tm(lambda: evaluate(circs[0], enc, V)); out["verdict_evaluate_s"].append(dt)
    out["verdict"] = dict(ok=v.ok, method=v.method, engine=v.engine, op=v.op_norm_error, gauss=v.gauss_residual, read=v.outer_bits_read)
elif mode == "robust":
    from su2plaq.compress import robust as RB
    calls = []
    n_first = 0 if cold else 1
    for i in range(n_first + nrep):
        dt, rec = tm(lambda: RB.robust_metrics("lsh", "step", path)); calls.append(dt)
    out.update(calls=calls, n_warmup=n_first, robust_key=rec["robust_key"], t_sum=rec["t_sum"], depth_sum=rec["depth_sum"], cx=rec["cx"], qubits=rec["qubits"],
               skeleton_equal=rec["skeleton_equal"], angle_linear=rec["angle_linear"], n_pairs=len(rec["t_eps"]))
out["rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
print("RESULT " + json.dumps(out), flush=True)
