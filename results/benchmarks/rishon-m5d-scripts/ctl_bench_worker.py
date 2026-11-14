"""Rishon M5 benchmark worker (tester, reports/benchmarks/200).  One task per FRESH process; prints one line
RESULT {task, times:{name:[s,...]}, rss_mb, cpu_start, cpu_end, load_start, load_end, out:{...}}.
Env: OMP/OPENBLAS/MKL_NUM_THREADS=1, PYTHONHASHSEED=20261104.  Seeds: verify gauss sample 20261104 (library default), ct_compile 12345.
Never edits src/ or tests/."""
import sys, os, json, time, resource
ROOT = os.environ.get("BENCH_ROOT", "/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, ROOT + "/src"); sys.path.insert(0, ROOT)
import numpy as np

task = sys.argv[1]
T, OUT = {}, {}
def getcpu():
    return int(open("/proc/self/stat").read().rsplit(")", 1)[1].split()[36])   # field 39 'processor'

cpu0, load0 = getcpu(), os.getloadavg()

def timed(name, f, reps=1):
    r = None
    for _ in range(reps):
        t0 = time.perf_counter(); r = f(); T.setdefault(name, []).append(time.perf_counter() - t0)
    return r

def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def finish():
    print("RESULT " + json.dumps({"task": task, "times": T, "rss_mb": rss(), "cpu_start": cpu0, "cpu_end": getcpu(),
                                  "load_start": load0, "load_end": os.getloadavg(), "out": OUT}, default=str), flush=True)

def vd(v):
    return dict(ok=v.ok, reason=v.reason, certified=v.certified, op_norm_error=v.op_norm_error, block_error=v.block_error,
                leak_amplitude=v.leak_amplitude, dropped_total=v.dropped_total, max_leak=v.max_leak, dirty_ancilla=v.dirty_ancilla,
                gauss_residual=v.gauss_residual, gauss_states=v.gauss_states, outer_bits_read=v.outer_bits_read, engine=v.engine,
                method=v.method, tolerances=v.tolerances, verdict_seconds=v.seconds)

ALPHA, BETA = 0.37, 0.61
EPS = (1e-4, 1e-6, 1e-8, 1e-10)

if task == "import":
    for name in ("numpy", "scipy.sparse", "qiskit", "qiskit_aer", "su2plaq.rishon.physical", "su2plaq.rishon.operators",
                 "su2plaq.circuits.rishon", "su2plaq.encodings.rishon", "su2plaq.evaluate.evaluator", "su2plaq.rishon.verify",
                 "su2plaq.metrics.cliffordt"):
        timed("import " + name, lambda n=name: __import__(n))
elif task == "basis":
    from su2plaq.rishon import physical as P
    b = timed("rishon_basis_cold", P.rishon_basis)
    OUT["rss_after_basis_mb"] = rss()
    OUT["dim"] = b.dim
    timed("counts", lambda: P.counts(b))
    timed("_build_basis_second_call_kernels_cached", P._build_basis)
    timed("rishon_basis_cached_call", P.rishon_basis, 3)
    S = timed("inner_span", lambda: P.inner_span(b))
    OUT["inner_span_shape"] = list(S.shape)
    from su2plaq.encodings.rishon import RishonEncoding
    timed("RishonEncoding()", RishonEncoding)
    timed("count_by_fusion", P.count_by_fusion)
elif task == "inner":
    from su2plaq.rishon import operators as O
    ops = timed("_sector_ops_cold", O._sector_ops)
    W = timed("_W_build_after_sector_ops", O._W.__wrapped__)
    timed("plaquette_W_inner_copy", O.plaquette_W_inner)
    HB = timed("h_magnetic_inner", O.h_magnetic_inner)
    w = None
    for i in range(3):
        t0 = time.perf_counter(); w, V = np.linalg.eigh(HB); T.setdefault("eigh_1296_complex128_with_vectors", []).append(time.perf_counter() - t0)
    for i in range(3):
        t0 = time.perf_counter(); np.linalg.eigvalsh(HB); T.setdefault("eigvalsh_1296_complex128", []).append(time.perf_counter() - t0)
    HBr = np.real(HB)
    for i in range(3):
        t0 = time.perf_counter(); np.linalg.eigh(HBr); T.setdefault("eigh_1296_real_with_vectors", []).append(time.perf_counter() - t0)
    OUT["eigenvalue_multiplicities"] = {f"{k:.6g}": int(n) for k, n in zip(*np.unique(np.round(w, 6), return_counts=True))}
    OUT["herm_err"] = float(np.abs(HB - HB.conj().T).max())
    OUT["recon_err"] = float(np.abs(HB @ V - V * w).max())
    timed("_bright_cold(81 comps eigh)", O._bright.__wrapped__)
    for kind, a, b_, o in (("UE", ALPHA, None, 1), ("UB", None, BETA, 1), ("step", ALPHA, BETA, 1), ("step", ALPHA, BETA, 2)):
        Vt = timed(f"inner_target_{kind}{o}", lambda k=kind, a=a, b_=b_, o=o: O.inner_target(k, a, b_, o), 3)
        OUT[f"unitarity_{kind}{o}"] = float(np.abs(Vt.conj().T @ Vt - np.eye(1296)).max())
    timed("closed_block_3x3", lambda: O.closed_block(1.0), 3)
elif task == "build":
    from su2plaq.circuits import rishon as C
    from su2plaq.metrics.logical import logical_metrics
    for name, f in (("build_UE", lambda: C.build_UE(ALPHA)), ("build_UB", lambda: C.build_UB(BETA)),
                    ("build_step1", lambda: C.build_step(ALPHA, BETA, 1)), ("build_step2", lambda: C.build_step(ALPHA, BETA, 2)),
                    ("build_UE_outer_row", lambda: C.build_UE(ALPHA, with_outer=True, include_outer_electric=True))):
        qc = timed(name, f, 5)
        lm = timed("logical_metrics_" + name[6:], lambda q=qc: logical_metrics(q), 3)
        OUT[name] = dict(nq=qc.num_qubits, macro_ops=dict(qc.count_ops()), macro_depth=qc.depth(),
                         **{k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")})
elif task.startswith("verify_"):
    kind_key = task.split("_", 1)[1]            # UE UB step step2
    from su2plaq.circuits import rishon as C
    from su2plaq.encodings.rishon import RishonEncoding
    from su2plaq.rishon.verify import verify
    enc = RishonEncoding()
    timed("rishon_basis_cold", lambda: enc.basis)
    spec = {"UE": (lambda: C.build_UE(ALPHA), "UE", ALPHA, None, 1), "UB": (lambda: C.build_UB(BETA), "UB", None, BETA, 1),
            "step": (lambda: C.build_step(ALPHA, BETA, 1), "step", ALPHA, BETA, 1),
            "step2": (lambda: C.build_step(ALPHA, BETA, 2), "step", ALPHA, BETA, 2)}[kind_key]
    qc = timed("build", spec[0])
    v = None
    for i in range(2):
        t0 = time.perf_counter(); v = verify(qc, enc, spec[1], spec[2], spec[3], spec[4]); T.setdefault("verify", []).append(time.perf_counter() - t0)
    OUT = vd(v)
elif task.startswith("ttable_"):
    kind_key = task.split("_", 1)[1]
    from su2plaq.circuits import rishon as C
    from su2plaq.metrics.cliffordt import t_table
    from su2plaq.metrics.logical import logical_metrics
    qc = {"UE": lambda: C.build_UE(ALPHA), "UB": lambda: C.build_UB(BETA), "step": lambda: C.build_step(ALPHA, BETA, 1),
          "step2": lambda: C.build_step(ALPHA, BETA, 2),
          "UE_outer_row": lambda: C.build_UE(ALPHA, with_outer=True, include_outer_electric=True),
          "UD": lambda: C.build_UD(0.29), "step3": lambda: C.build_step(ALPHA, BETA, 1, eta=0.29)}[kind_key]()
    lm = timed("logical_metrics", lambda: logical_metrics(qc), 3)
    OUT["logical"] = {k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}
    OUT["gates_lowered"] = lm["gates"]
    rows0 = timed("t_table_qiskit_False_cold", lambda: t_table(qc, EPS, qiskit=False))
    timed("t_table_qiskit_False_warm", lambda: t_table(qc, EPS, qiskit=False), 2)
    rows = timed("t_table_qiskit_True", lambda: t_table(qc, EPS, qiskit=True), 2)
    OUT["t_table"] = rows
    OUT["pygridsynth_only_matches"] = [(a["t_total"], b["t_total"]) for a, b in zip(rows0, rows)]
elif task.startswith("synth_"):
    kind_key, eps = task.split("_")[1], float(task.split("_")[2])
    from su2plaq.circuits import rishon as C
    from su2plaq.encodings.rishon import RishonEncoding
    from su2plaq.metrics.cliffordt import synthesize
    from su2plaq.rishon.verify import synth_tolerances, verify
    enc = RishonEncoding(); timed("rishon_basis_cold", lambda: enc.basis)
    spec = {"UE": (lambda: C.build_UE(ALPHA), "UE", ALPHA, None, 1), "UB": (lambda: C.build_UB(BETA), "UB", None, BETA, 1),
            "step": (lambda: C.build_step(ALPHA, BETA, 1), "step", ALPHA, BETA, 1)}[kind_key]
    qc = spec[0]()
    s, info = timed("synthesize_cold", lambda: synthesize(qc, eps))
    tol = synth_tolerances(info["n_rot"], eps)
    v = timed("verify_synth", lambda: verify(s, enc, spec[1], spec[2], spec[3], spec[4], **tol))
    OUT = vd(v); OUT.update(n_rot=info["n_rot"], t_rot=info["t_rot"], err_bound=info["error_bound_sum"], err_meas=info["error_measured_sum"],
                            tol=tol, n_gates=len(s.data), nq=s.num_qubits, eps=eps)
elif task == "build_det":
    from su2plaq.circuits import rishon as C
    from su2plaq.metrics.logical import logical_metrics
    ETA = 0.29
    for name, f in (("build_UD", lambda: C.build_UD(ETA)), ("build_UD_outer_row", lambda: C.build_UD(ETA, with_outer=True, include_outer_det=True)),
                    ("build_step3_order1", lambda: C.build_step(ALPHA, BETA, 1, eta=ETA)), ("build_step3_order2", lambda: C.build_step(ALPHA, BETA, 2, eta=ETA))):
        qc = timed(name, f, 5)
        lm = timed("logical_metrics_" + name[6:], lambda q=qc: logical_metrics(q), 3)
        OUT[name] = dict(nq=qc.num_qubits, macro_ops=dict(qc.count_ops()), macro_depth=qc.depth(),
                         **{k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")})
elif task.startswith("verifydet_"):
    kind_key = task.split("_", 1)[1]            # UD step3 step3_order2
    from su2plaq.circuits import rishon as C
    from su2plaq.encodings.rishon import RishonEncoding
    from su2plaq.rishon.verify import verify
    ETA = 0.29
    enc = RishonEncoding()
    timed("rishon_basis_cold", lambda: enc.basis)
    spec = {"UD": (lambda: C.build_UD(ETA), "UD", None, None, 1), "step3": (lambda: C.build_step(ALPHA, BETA, 1, eta=ETA), "step", ALPHA, BETA, 1),
            "step3_order2": (lambda: C.build_step(ALPHA, BETA, 2, eta=ETA), "step", ALPHA, BETA, 2)}[kind_key]
    qc = timed("build", spec[0])
    v = None
    for i in range(2):
        t0 = time.perf_counter(); v = verify(qc, enc, spec[1], spec[2], spec[3], spec[4], eta=ETA); T.setdefault("verify", []).append(time.perf_counter() - t0)
    OUT = vd(v)
elif task == "threelayer":
    from su2plaq.rishon.compress import three_layer as TL
    r = timed("verify_three_layer_r04-F1-004", lambda: TL.verify_three_layer("r04-F1-004"))
    OUT = {k: r[k] for k in r if k != "verdicts"}; OUT["verdicts"] = r["verdicts"]
    timed("det_layer_metrics", TL.det_layer_metrics)
elif task.startswith("synthdet_"):
    kind_key, eps = task.split("_")[1], float(task.split("_")[2])
    from su2plaq.circuits import rishon as C
    from su2plaq.encodings.rishon import RishonEncoding
    from su2plaq.metrics.cliffordt import synthesize
    from su2plaq.rishon.verify import synth_tolerances, verify
    ETA = 0.29
    enc = RishonEncoding(); timed("rishon_basis_cold", lambda: enc.basis)
    spec = {"UD": (lambda: C.build_UD(ETA), "UD", None, None, 1), "step3": (lambda: C.build_step(ALPHA, BETA, 1, eta=ETA), "step", ALPHA, BETA, 1)}[kind_key]
    qc = spec[0]()
    s, info = timed("synthesize_cold", lambda: synthesize(qc, eps))
    tol = synth_tolerances(info["n_rot"], eps)
    v = timed("verify_synth", lambda: verify(s, enc, spec[1], spec[2], spec[3], spec[4], eta=ETA, **tol))
    OUT = vd(v); OUT.update(n_rot=info["n_rot"], t_rot=info["t_rot"], n_gates=len(s.data), nq=s.num_qubits, eps=eps)
else:
    raise SystemExit("unknown task " + task)
finish()
