"""M3 benchmark worker (tester, reports/benchmarks/100).  One task per fresh process.
usage: python bench_worker_m3.py <task> -> prints  RESULT {task, times:{name:[...]}, rss_mb, out:{...}}
Env: OMP/OPENBLAS/MKL_NUM_THREADS=1, PYTHONHASHSEED=20261104.  No stochastic call is timed (ct_compile not used here)."""
import sys, json, time, resource, pathlib
ROOT = str(pathlib.Path(__file__).resolve().parents[3])
sys.path.insert(0, ROOT + "/src")
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
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
T["import_evaluator"] = [time.perf_counter() - t0]

if task == "enc_build":
    t0 = time.perf_counter()
    from su2plaq.encodings.spinnet import SpinNet
    T["import_spinnet"] = [time.perf_counter() - t0]
    enc = None
    for i in range(4):
        t0 = time.perf_counter(); enc = SpinNet(); T.setdefault("SpinNet()", []).append(time.perf_counter() - t0)
    timed("target_UB", lambda: enc.target("UB", None, beta), 3)
    timed("inner_target_UB", lambda: enc.inner_target("UB", None, beta), 3)
    OUT = dict(n_phys=len(enc.basis.labels), n_inner=len(enc.inner_codes()), gauge_residual=enc.gauge_residual)
    finish(); sys.exit()

if task == "eval_twelve_UB":
    from su2plaq.circuits import twelve as C
    from su2plaq.encodings.twelve import TwelveQubit
    enc = TwelveQubit(); qc = C.build_UB(beta); V = enc.target("UB", None, beta)
    for i in range(4):
        t0 = time.perf_counter(); v = evaluate(qc, enc, V); T.setdefault("evaluate", []).append(time.perf_counter() - t0)
    OUT = vd(v); finish(); sys.exit()

from su2plaq.circuits import spinnet as C
from su2plaq.encodings.spinnet import SpinNet, align_inner_block
from su2plaq.evaluate.sparse_sim import encoded_block, run_batch
from su2plaq.metrics.cliffordt import synthesize
t0 = time.perf_counter(); enc = SpinNet(); T["SpinNet()_in_task"] = [time.perf_counter() - t0]

def run(name, qc, V, reps=4, **kw):
    v = None
    for i in range(reps):
        t0 = time.perf_counter(); v = evaluate(qc, enc, V, **kw); T.setdefault(name, []).append(time.perf_counter() - t0)
    return v

if task == "eval_UB_outer_physical":
    t0 = time.perf_counter(); qc = C.build_UB(beta, with_outer=True); T["build_UB_outer_cold"] = [time.perf_counter() - t0]
    timed("build_UB_outer_warm", lambda: C.build_UB(beta, with_outer=True), 3)
    V = enc.target("UB", None, beta)
    OUT = vd(run("evaluate", qc, V, method="physical")); OUT["ops"] = dict(qc.count_ops()); OUT["nq"] = qc.num_qubits
elif task == "eval_UB_auto":
    qc = C.build_UB(beta); V = enc.target("UB", None, beta)
    OUT = vd(run("evaluate", qc, V)); OUT["ops"] = dict(qc.count_ops())
elif task in ("eval_step1", "eval_step2"):
    o = 1 if task.endswith("1") else 2
    t0 = time.perf_counter(); qc = C.build_step(alpha, beta, o); T["build_step_cold"] = [time.perf_counter() - t0]
    timed("build_step_warm", lambda: C.build_step(alpha, beta, o), 3)
    V = enc.target("step", alpha, beta, o)
    OUT = vd(run("evaluate", qc, V)); OUT["ops"] = dict(qc.count_ops())
elif task == "eval_UE":
    qc = C.build_UE(alpha); V = enc.target("UE", alpha, None)
    OUT = vd(run("evaluate", qc, V))
elif task == "eval_paulo15":
    bP = C.paulo.FILE_ALPHA_P / 2
    t0 = time.perf_counter(); qc = C.paulo_circuit(); T["load_paulo"] = [time.perf_counter() - t0]
    def align():
        codes = enc.inner_codes()
        M, leak = encoded_block(run_batch(qc, codes), codes, len(codes), code_mask=(1 << 8) - 1)
        D, res, ph = align_inner_block(M, enc.inner_target("UB", None, bP))
        return D, res
    D, res = timed("gauge_alignment", align)
    qo = C.paulo_circuit(with_outer=True)
    Vg = enc.regauge(enc.target("UB", None, bP), D)
    OUT = vd(run("evaluate", qo, Vg, method="physical", gauss=True)); OUT["ops"] = dict(qo.count_ops()); OUT["nq"] = qo.num_qubits
    OUT["align_res"] = float(res)
elif task in ("eval_pairs9", "eval_flags4"):
    name = task.split("_")[1]
    qc = C.trotter_v2_circuit(name, beta); V = enc.target("UB", None, beta)
    OUT = vd(run("evaluate", qc, V)); OUT["ops"] = dict(qc.count_ops()); OUT["nq"] = qc.num_qubits
elif task in ("synth_UB", "synth_step1"):
    if task == "synth_UB": qc, V = C.build_UB(beta), enc.target("UB", None, beta)
    else: qc, V = C.build_step(alpha, beta, 1), enc.target("step", alpha, beta, 1)
    eps = 1e-6; sy = None
    for i in range(3):
        t0 = time.perf_counter(); sy = synthesize(qc, eps); T.setdefault("synthesize", []).append(time.perf_counter() - t0)
    s, info = sy
    tol = synth_tolerances(info["n_rot"], eps)
    OUT = vd(run("evaluate_synth", s, V, reps=3, engine="sparse", **tol))
    OUT.update(n_rot=info["n_rot"], t_rot=info["t_rot"], err_bound=info["error_bound_sum"], err_meas=info["error_measured_sum"], tol=tol, n_gates=len(s.data), nq=s.num_qubits)
else:
    raise SystemExit("unknown task " + task)
finish()
