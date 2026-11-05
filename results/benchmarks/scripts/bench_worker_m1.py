"""M1 benchmark worker (tester, reports/benchmarks/002).  One task per fresh process; same conventions as bench_worker.py (M0).
usage: python bench_worker_m1.py <task>  -> prints one line  RESULT {task, times:{name:[...]}, rss_mb, out:{...}}
Env: OMP/OPENBLAS/MKL_NUM_THREADS=1, PYTHONHASHSEED=20261104.  Seed 20261104; ct_compile seed 12345 (default); no stochastic call timed."""
import sys, json, time, resource
ROOT = "/home/digimonk/Projects/su2qc-encoding"
sys.path.insert(0, ROOT + "/src"); sys.path.insert(0, ROOT)
import numpy as np

task = sys.argv[1]
T = {}; OUT = {}

def timed(name, f, reps=1):
    r = None
    for _ in range(reps):
        t0 = time.perf_counter(); r = f(); T.setdefault(name, []).append(time.perf_counter() - t0)
    return r

def finish():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print("RESULT " + json.dumps({"task": task, "times": T, "rss_mb": rss, "out": OUT}, default=str), flush=True)

def vd(v):
    return dict(ok=v.ok, reason=v.reason, op=v.op_norm_error, block=v.block_error, leak_amp=v.leak_amplitude, gauss=v.gauss_residual,
                engine=v.engine, method=v.method, read=v.outer_bits_read, n_blocks=v.n_blocks, certified=v.certified,
                max_leak=v.max_leak, dirty=v.dirty_ancilla, acc=v.engine_accuracy, verdict_seconds=v.seconds)

alpha, beta = 0.37, 0.61
t0 = time.perf_counter()
from su2plaq.circuits import twelve as C
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.metrics.cliffordt import synthesize
T["import"] = [time.perf_counter() - t0]

if task == "m1_build":
    for name, f in (("build_UE", lambda: C.build_UE(alpha)), ("build_UB", lambda: C.build_UB(beta)),
                    ("build_step1", lambda: C.build_step(alpha, beta, 1)), ("build_step2", lambda: C.build_step(alpha, beta, 2))):
        qc = timed(name, f, 4)
        OUT[name] = dict(ops=dict(qc.count_ops()), nq=qc.num_qubits, gphase=qc.global_phase)
elif task in ("eval_UE", "eval_UB", "eval_step1", "eval_step2"):
    enc = TwelveQubit()
    qc, V = {"eval_UE": lambda: (C.build_UE(alpha), enc.target("UE", alpha, None)),
             "eval_UB": lambda: (C.build_UB(beta), enc.target("UB", None, beta)),
             "eval_step1": lambda: (C.build_step(alpha, beta, 1), enc.target("step", alpha, beta, 1)),
             "eval_step2": lambda: (C.build_step(alpha, beta, 2), enc.target("step", alpha, beta, 2))}[task]()
    vs = []
    for i in range(4):
        t0 = time.perf_counter(); v = evaluate(qc, enc, V); T.setdefault("evaluate", []).append(time.perf_counter() - t0); vs.append(v)
    OUT = vd(vs[-1])
elif task in ("synth_UB", "synth_step1", "synth_step2"):
    enc = TwelveQubit(); eps = 1e-6
    if task == "synth_UB": qc, V = C.build_UB(beta), enc.target("UB", None, beta)
    elif task == "synth_step1": qc, V = C.build_step(alpha, beta, 1), enc.target("step", alpha, beta, 1)
    else: qc, V = C.build_step(alpha, beta, 2), enc.target("step", alpha, beta, 2)
    sy = None
    for i in range(3):
        t0 = time.perf_counter(); sy = synthesize(qc, eps); T.setdefault("synthesize", []).append(time.perf_counter() - t0)
    s, info = sy
    tol = synth_tolerances(info["n_rot"], eps)
    vs = []
    for i in range(3):
        t0 = time.perf_counter(); v = evaluate(s, enc, V, **tol); T.setdefault("evaluate_synth", []).append(time.perf_counter() - t0); vs.append(v)
    OUT = vd(vs[-1]); OUT.update(n_rot=info["n_rot"], t_rot=info["t_rot"], err_bound=info["error_bound_sum"], err_meas=info["error_measured_sum"],
                                 tol=tol, n_gates=len(s.data), nq=s.num_qubits)
elif task == "paulo_m1":
    enc = TwelveQubit()
    qc = timed("paulo_circuit_load", lambda: C.paulo_circuit())
    V = enc.target("UB", None, 1.0)
    v = timed("evaluate_paulo", lambda: evaluate(qc, enc, V, engine="auto", tol_err=2e-5, tol_gauss=2e-5))
    OUT = vd(v); OUT["nqubits"] = qc.num_qubits
else:
    raise SystemExit("unknown task")
finish()
