"""M0 baseline benchmark worker (tester, reports/benchmarks/001).  One task per fresh process.
usage: python bench_worker.py <task>   -> prints one JSON line: {task, times:{name:[...]}, rss_mb, out:{...}}
Env: OMP/OPENBLAS/MKL_NUM_THREADS=1.  Seed 20261104 (no stochastic call in the benchmark; ct_compile seed 12345 = default)."""
import sys, json, time, resource, os
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

alpha, beta = 0.37, 0.61

if task == "basis":
    t0 = time.perf_counter()
    from su2plaq.exact.physical import physical_basis, counts, _build_cg
    from su2plaq.geometry import plaquette_diagram
    T["import"] = [time.perf_counter() - t0]
    b = timed("physical_basis_cold", lambda: physical_basis())
    timed("physical_basis_cached_lookup", lambda: physical_basis(), 5)
    timed("physical_basis_rebuild_warm_lru", lambda: physical_basis(diagram=plaquette_diagram()), 3)
    OUT["counts"] = {k: (v if not hasattr(v, "tolist") else v.tolist()) for k, v in counts(b).items()}
    OUT["dim"] = b.dim
elif task == "ops":
    from su2plaq.exact.physical import physical_basis
    from su2plaq.exact.operators import h_magnetic_phys, target
    from su2plaq.exact import spinnet
    b = physical_basis()
    HB, leak = timed("h_magnetic_phys", lambda: h_magnetic_phys(b), 4)
    ev = np.linalg.eigvalsh(HB)
    OUT["hb_spec"] = {str(k): int(v) for k, v in zip(*np.unique(np.round(ev, 6), return_counts=True))}
    OUT["hb_leak"] = leak; OUT["hb_fro"] = float(np.linalg.norm(HB)); OUT["hb_herm"] = float(np.abs(HB - HB.conj().T).max())
    St = timed("target_step", lambda: target(b, "step", alpha, beta), 4)
    OUT["step_unitarity"] = float(np.abs(St.conj().T @ St - np.eye(b.dim)).max()); OUT["step_fro_trace"] = [float(np.linalg.norm(St)), complex(np.trace(St)).real, complex(np.trace(St)).imag]
    UB = timed("target_UB", lambda: target(b, "UB", None, beta), 2)
    UE = timed("target_UE", lambda: target(b, "UE", alpha), 2)
    OUT["ub_trace"] = [complex(np.trace(UB)).real, complex(np.trace(UB)).imag]
    labs = timed("labels_6j", lambda: spinnet.labels(jmax=0.5), 3)
    HB6 = timed("h_magnetic_phys_6j", lambda: spinnet.h_magnetic_phys_6j(labs), 4)
    e6 = np.linalg.eigvalsh(HB6)
    OUT["spec_A_vs_B_maxdiff"] = float(np.abs(np.sort(ev) - np.sort(e6)).max()); OUT["n_labels"] = len(labs)
    OUT["hb6_spec"] = {str(k): int(v) for k, v in zip(*np.unique(np.round(e6, 6), return_counts=True))}
elif task.startswith("eval_"):
    from qiskit import QuantumCircuit, QuantumRegister
    from su2plaq.encodings.twelve import TwelveQubit
    from su2plaq.evaluate.evaluator import evaluate
    from su2plaq.exact.operators import target
    enc = TwelveQubit(); basis = enc.basis; I = np.eye(433, dtype=complex)
    def circ(outer=False):
        regs = [QuantumRegister(12, "d")] + ([QuantumRegister(16, "o")] if outer else [])
        return QuantumCircuit(*regs), regs
    kw = {}
    if task == "eval_id_span":
        qc, _ = circ(); V = I; kw = dict(method="inner_span")
    elif task == "eval_id_phys":
        qc, _ = circ(); V = I; kw = dict(method="physical")
    elif task == "eval_ue":
        qc, r = circ()
        for q in (2, 5, 8, 11): qc.p(-0.75 * alpha, r[0][q])
        V = target(basis, "UE", alpha=alpha)
    elif task == "eval_outer3":
        qc, r = circ(True)
        for k in (0, 1, 2): qc.p(-0.75 * alpha, r[1][2 * k + 1])
        ph = np.array([-alpha * sum(j * (j + 1) for j in lab[0][4:7]) for lab in basis.labels])
        V = np.diag(np.exp(1j * ph))
    # untimed warm of encoding caches is NOT done: first call includes evaluator's lazy _phys_data build
    vs = []
    for i in range(4):
        t0 = time.perf_counter(); v = evaluate(qc, enc, V, **kw); T.setdefault("evaluate", []).append(time.perf_counter() - t0); vs.append(v)
    v = vs[-1]
    OUT = dict(ok=v.ok, reason=v.reason, op=v.op_norm_error, block=v.block_error, leak_amp=v.leak_amplitude, gauss=v.gauss_residual,
               engine=v.engine, method=v.method, read=v.outer_bits_read, n_blocks=v.n_blocks, certified=v.certified, verdict_seconds=[x.seconds for x in vs])
elif task == "paulo_eval":
    from qiskit import qpy
    from su2plaq.encodings.twelve import TwelveQubit
    from su2plaq.evaluate.evaluator import evaluate
    enc = TwelveQubit(); qc = qpy.load(open(ROOT + "/refs/paulo/SU2_plaquette_jmax_half_CT.qpy", "rb"))[0]
    V = enc.target("UB", None, 1.0)
    v = timed("evaluate_paulo", lambda: evaluate(qc, enc, V, engine="auto", tol_err=2e-5, tol_gauss=2e-5))
    OUT = dict(ok=v.ok, reason=v.reason, op=v.op_norm_error, block=v.block_error, leak_amp=v.leak_amplitude, max_leak=v.max_leak, dirty=v.dirty_ancilla,
               gauss=v.gauss_residual, engine=v.engine, method=v.method, certified=v.certified, acc=v.engine_accuracy, read=v.outer_bits_read,
               n_blocks=v.n_blocks, verdict_seconds=v.seconds, nqubits=qc.num_qubits)
elif task in ("metrics", "metrics_q", "metrics_c"):
    from qiskit import QuantumCircuit, QuantumRegister
    nb = json.load(open(ROOT + "/refs/paulo/optimized_plaquette_dontcare_lowT.ipynb"))
    g = {"np": np, "QuantumCircuit": QuantumCircuit, "QuantumRegister": QuantumRegister}
    def rebuild():
        for i in [3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]:
            exec("".join(nb["cells"][i]["source"]), g)
        return g["optimized_plaquette_dontcare_low_t"](dt=1.0, gs=1.0, gt=1.0, a=1.0)
    qc, _ = timed("rebuild_paulo_uncompiled", rebuild)
    from su2plaq.metrics.logical import logical_metrics
    from su2plaq.metrics.cliffordt import ct_compile, t_table
    if task == "metrics_c":  # ct_compile first in a fresh process
        out, cm = timed("ct_compile_1e-6_L3", lambda: ct_compile(qc, 1e-6, 3, 12345), 3)
        OUT["ct_compile"] = cm
        finish(); sys.exit(0)
    if task == "metrics_q":  # order variant: Qiskit-compiling calls first (cold pygridsynth cache inside t_table True)
        rowsq = timed("t_table_qiskit_True", lambda: t_table(qc, qiskit=True), 3)
        out, cm = timed("ct_compile_1e-6_L3", lambda: ct_compile(qc, 1e-6, 3, 12345), 3)
        OUT["ct_compile"] = cm; OUT["t_table_True"] = rowsq
        finish(); sys.exit(0)
    m = timed("logical_metrics", lambda: logical_metrics(qc), 4)
    OUT["logical"] = {k: v for k, v in m.items() if k != "rz_angles"}
    rows0 = timed("t_table_qiskit_False", lambda: t_table(qc, qiskit=False), 3)
    rows1 = timed("t_table_qiskit_True", lambda: t_table(qc, qiskit=True), 3)
    OUT["t_table_False"] = rows0; OUT["t_table_True"] = rows1
    out, cm = timed("ct_compile_1e-6_L3", lambda: ct_compile(qc, 1e-6, 3, 12345), 3)
    OUT["ct_compile"] = cm
else:
    raise SystemExit("unknown task")
finish()
