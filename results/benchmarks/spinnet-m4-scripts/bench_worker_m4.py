"""M4 / M7 benchmark worker (tester, reports/benchmarks/301 and 302).  One task per fresh process.
usage: python bench_worker_m4.py <task> [scratch_dir]  -> prints  RESULT {task, times:{name:[...]}, rss_mb, out:{...}}
Extends results/benchmarks/spinnet-m3-scripts/bench_worker_m3.py (same task names for the spin-network tasks) with the
M4 headline circuit, route A (exact) tasks, the compression-evaluator task and the LSH tasks.
Env: OMP/OPENBLAS/MKL_NUM_THREADS=1, PYTHONHASHSEED=20261104.  No stochastic call is timed."""
import sys, json, time, resource, pathlib, tempfile
ROOT = str(pathlib.Path(__file__).resolve().parents[3])
sys.path.insert(0, ROOT + "/src")
import numpy as np

task = sys.argv[1]
SCR = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(tempfile.mkdtemp())
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
from su2plaq.metrics.cliffordt import synthesize
from su2plaq.metrics.logical import logical_metrics

def run(name, enc, qc, V, reps=4, **kw):
    v = None
    for i in range(reps):
        t0 = time.perf_counter(); v = evaluate(qc, enc, V, **kw); T.setdefault(name, []).append(time.perf_counter() - t0)
    return v

def synth_eval(qc, enc, V, eps=1e-6):
    sy = None
    for i in range(3):
        t0 = time.perf_counter(); sy = synthesize(qc, eps); T.setdefault("synthesize", []).append(time.perf_counter() - t0)
    s, info = sy
    tol = synth_tolerances(info["n_rot"], eps)
    out = vd(run("evaluate_synth", enc, s, V, reps=3, engine="sparse", **tol))
    out.update(n_rot=info["n_rot"], t_rot=info["t_rot"], err_bound=info["error_bound_sum"], n_gates=len(s.data), nq=s.num_qubits)
    return out

# ---------------------------------------------------------------- route A (exact side), as bench_worker.py "ops" / "basis" of 001-003
if task == "ops":
    from su2plaq.exact.physical import physical_basis
    from su2plaq.exact.operators import h_magnetic_phys, target
    from su2plaq.exact import spinnet
    b = timed("physical_basis_cold", lambda: physical_basis())
    HB, leak = timed("h_magnetic_phys", lambda: h_magnetic_phys(b), 4)
    ev = np.linalg.eigvalsh(HB)
    OUT["hb_spec"] = {str(k): int(v) for k, v in zip(*np.unique(np.round(ev, 6), return_counts=True))}
    OUT["hb_leak"] = leak; OUT["hb_fro"] = float(np.linalg.norm(HB)); OUT["hb_herm"] = float(np.abs(HB - HB.conj().T).max())
    St = timed("target_step", lambda: target(b, "step", alpha, beta), 4)
    OUT["step_unitarity"] = float(np.abs(St.conj().T @ St - np.eye(b.dim)).max())
    UB = timed("target_UB", lambda: target(b, "UB", None, beta), 2)
    UE = timed("target_UE", lambda: target(b, "UE", alpha), 2)
    OUT["ub_trace"] = [complex(np.trace(UB)).real, complex(np.trace(UB)).imag]
    labs = timed("labels_6j", lambda: spinnet.labels(jmax=0.5), 3)
    HB6 = timed("h_magnetic_phys_6j", lambda: spinnet.h_magnetic_phys_6j(labs), 4)
    OUT["spec_A_vs_B_maxdiff"] = float(np.abs(np.sort(ev) - np.sort(np.linalg.eigvalsh(HB6))).max()); OUT["dim"] = b.dim
    finish(); sys.exit()

if task == "eval_twelve_UB":
    from su2plaq.circuits import twelve as C
    from su2plaq.encodings.twelve import TwelveQubit
    enc = TwelveQubit(); qc = C.build_UB(beta); V = enc.target("UB", None, beta)
    OUT = vd(run("evaluate", enc, qc, V)); finish(); sys.exit()

# ---------------------------------------------------------------- LSH
if task.startswith("lsh_"):
    from su2plaq.circuits import lsh as CL
    from su2plaq.circuits import spinnet as CS
    t0 = time.perf_counter()
    from su2plaq.encodings.lsh import LSH
    T["import_lsh"] = [time.perf_counter() - t0]
    if task == "lsh_enc_build":
        enc = None
        for i in range(4):
            t0 = time.perf_counter(); enc = LSH(); T.setdefault("LSH()", []).append(time.perf_counter() - t0)
        timed("target_UB", lambda: enc.target("UB", None, beta), 3)
        timed("target_step", lambda: enc.target("step", alpha, beta, 1), 3)
        timed("build_UE", lambda: CL.build_UE(alpha), 4)
        timed("build_UB", lambda: CL.build_UB(beta), 4)
        timed("build_step1", lambda: CL.build_step(alpha, beta, 1), 4)
        timed("build_step2", lambda: CL.build_step(alpha, beta, 2), 4)
        OUT = dict(n_phys=len(enc.basis.labels), n_inner=len(enc.inner_codes()))
        finish(); sys.exit()
    t0 = time.perf_counter(); enc = LSH(); T["LSH()_in_task"] = [time.perf_counter() - t0]
    if task == "lsh_eval_UE":
        qc = CL.build_UE(alpha); OUT = vd(run("evaluate", enc, qc, enc.target("UE", alpha, None)))
    elif task == "lsh_eval_UB":
        qc = CL.build_UB(beta); OUT = vd(run("evaluate", enc, qc, enc.target("UB", None, beta)))
    elif task in ("lsh_eval_step1", "lsh_eval_step2"):
        o = int(task[-1]); qc = CL.build_step(alpha, beta, o)
        OUT = vd(run("evaluate", enc, qc, enc.target("step", alpha, beta, o)))
    elif task in ("lsh_eval_wrap_flags4", "lsh_eval_wrap_pairs9", "lsh_eval_wrap_general7"):
        nm = task.split("_")[-1]
        sn = CS.build_UB(beta) if nm == "general7" else CS.trotter_v2_circuit(nm, beta)
        qc = CL.wrap_spinnet(sn); OUT = vd(run("evaluate", enc, qc, enc.target("UB", None, beta)))
    elif task in ("lsh_synth_UE", "lsh_synth_UB", "lsh_synth_step1"):
        if task.endswith("UE"): qc, V = CL.build_UE(alpha), enc.target("UE", alpha, None)
        elif task.endswith("UB"): qc, V = CL.build_UB(beta), enc.target("UB", None, beta)
        else: qc, V = CL.build_step(alpha, beta, 1), enc.target("step", alpha, beta, 1)
        OUT = synth_eval(qc, enc, V)
    elif task == "lsh_lean_cert":
        from su2plaq.lsh import lean_export as LE
        qc = CL.build_step(alpha, beta, 1, with_outer=True)
        out_dir = SCR / f"lsh_certs_{int(time.time()*1000)}"
        r = None
        t0 = time.perf_counter(); r = LE.certify(qc, enc, "step", alpha, beta, 1, out_dir=out_dir)
        T["certify_total"] = [time.perf_counter() - t0]
        T["check_seconds"] = [r["check_seconds"]]; T["export_seconds"] = [r["seconds"] - r["check_seconds"]]
        OUT = {k: r[k] for k in ("status", "reason", "checker_sha256")}
    else:
        raise SystemExit("unknown task " + task)
    finish(); sys.exit()

# ---------------------------------------------------------------- spin network
from su2plaq.circuits import spinnet as C
from su2plaq.encodings.spinnet import SpinNet, align_inner_block
from su2plaq.evaluate.sparse_sim import encoded_block, run_batch

if task == "enc_build":
    t0 = time.perf_counter()
    from su2plaq.encodings import spinnet as _s
    T["import_spinnet"] = [time.perf_counter() - t0]
    enc = None
    for i in range(4):
        t0 = time.perf_counter(); enc = SpinNet(); T.setdefault("SpinNet()", []).append(time.perf_counter() - t0)
    timed("target_UB", lambda: enc.target("UB", None, beta), 3)
    timed("inner_target_UB", lambda: enc.inner_target("UB", None, beta), 3)
    OUT = dict(n_phys=len(enc.basis.labels), n_inner=len(enc.inner_codes()), gauge_residual=enc.gauge_residual)
    finish(); sys.exit()

t0 = time.perf_counter(); enc = SpinNet(); T["SpinNet()_in_task"] = [time.perf_counter() - t0]

def headline_circuit():
    """the M4 headline r02-F1-002 rebuilt from its archived program in the sandbox subprocess (sha256 checked), as scripts/m4_results.py"""
    from su2plaq.compress import archive as A
    from su2plaq.compress import round as R
    from su2plaq.spinnet import loop as L
    L.install(); sp = L.spec()
    arch = A.Archive.load(L.ENC, root=pathlib.Path(ROOT), n_alt=len(sp.alt_angles), strict=True)
    head = {e.id: e for e in arch.entries()}["r02-F1-002"]
    t0 = time.perf_counter()
    circ, err = R._circuit_of(sp, head.program_path, head.id, None, pathlib.Path(ROOT), expected_sha256=head.program_sha256)
    T["headline_build_in_sandbox"] = [time.perf_counter() - t0]
    if circ is None: raise SystemExit("headline build failed: " + str(err))
    return circ

if task == "eval_UB_outer_physical":
    qc = C.build_UB(beta, with_outer=True)
    OUT = vd(run("evaluate", enc, qc, enc.target("UB", None, beta), method="physical")); OUT["nq"] = qc.num_qubits
elif task == "eval_UB_auto":
    qc = timed("build_UB", lambda: C.build_UB(beta), 3); OUT = vd(run("evaluate", enc, qc, enc.target("UB", None, beta)))
elif task in ("eval_step1", "eval_step2"):
    o = int(task[-1]); qc = timed("build_step", lambda: C.build_step(alpha, beta, o), 3)
    OUT = vd(run("evaluate", enc, qc, enc.target("step", alpha, beta, o)))
elif task == "eval_UE":
    OUT = vd(run("evaluate", enc, C.build_UE(alpha), enc.target("UE", alpha, None)))
elif task in ("eval_pairs9", "eval_flags4"):
    qc = C.trotter_v2_circuit(task.split("_")[1], beta); OUT = vd(run("evaluate", enc, qc, enc.target("UB", None, beta))); OUT["nq"] = qc.num_qubits
elif task == "eval_headline":
    qc = headline_circuit(); lm = logical_metrics(qc)
    OUT = vd(run("evaluate", enc, qc, enc.target("step", alpha, beta, 1))); OUT["logical"] = {k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}
elif task == "synth_UB":
    OUT = synth_eval(C.build_UB(beta), enc, enc.target("UB", None, beta))
elif task == "synth_step1":
    OUT = synth_eval(C.build_step(alpha, beta, 1), enc, enc.target("step", alpha, beta, 1))
elif task == "synth_headline":
    OUT = synth_eval(headline_circuit(), enc, enc.target("step", alpha, beta, 1))
elif task == "lean_cert_headline":
    from su2plaq.spinnet import lean_export as LE
    qc = headline_circuit(); out_dir = SCR / f"sn_certs_{int(time.time()*1000)}"
    t0 = time.perf_counter(); r = LE.certify(qc, enc, "step", alpha, beta, 1, out_dir=out_dir); T["certify_total"] = [time.perf_counter() - t0]
    T["check_seconds"] = [r["check_seconds"]]; OUT = {k: r[k] for k in ("status", "reason", "checker_sha256")}
elif task == "eval_paulo15":
    bP = C.paulo.FILE_ALPHA_P / 2
    qc = timed("load_paulo", lambda: C.paulo_circuit())
    def align():
        codes = enc.inner_codes()
        M, leak = encoded_block(run_batch(qc, codes), codes, len(codes), code_mask=(1 << 8) - 1)
        return align_inner_block(M, enc.inner_target("UB", None, bP))
    D, res, ph = timed("gauge_alignment", align)
    qo = C.paulo_circuit(with_outer=True); Vg = enc.regauge(enc.target("UB", None, bP), D)
    OUT = vd(run("evaluate", enc, qo, Vg, method="physical", gauss=True)); OUT["align_res"] = float(res)
else:
    raise SystemExit("unknown task " + task)
finish()
