"""Tester step 1.3: counts of build_UB(0.61), rotation qubits, outer untouched, T(eps), synthesis feasibility on the sparse engine.
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_ub_counts_synth.py out.json"""
import sys, json, time, subprocess, warnings, resource
import numpy as np
warnings.filterwarnings("ignore")
from qiskit.circuit.library import RZGate
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_UB
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.metrics.logical import logical_metrics, lower
from su2plaq.metrics.cliffordt import synthesize, t_table, pygridsynth_tcount

enc = TwelveQubit(); beta = 0.61
out = dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted", beta=beta)
qc = build_UB(beta); qo = build_UB(beta, with_outer=True)
lm = logical_metrics(qc); lmo = logical_metrics(qo)
out["metrics"] = {k: lm[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits", "ancilla")}
out["metrics_with_outer"] = {k: lmo[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits", "ancilla")}
out["gates_level0"] = lm["gates"]; out["native_gate_names"] = dict(qc.count_ops())
print(out["metrics"], out["metrics_with_outer"]); print(lm["gates"]); print("native:", qc.count_ops())
# independent count of CX/T/rotation from the lowered circuit
low = lower(qc)
rot_qubits = sorted({low.find_bit(i.qubits[0]).index for i in low.data if i.operation.name == "rz" and abs(((float(i.operation.params[0]) / (np.pi / 4)) % 1)) > 1e-9 and abs(((float(i.operation.params[0]) / (np.pi / 4)) % 1) - 1) > 1e-9})
names = {}
for r in qc.qregs:
    for k, q in enumerate(r): names[qc.find_bit(q).index] = f"{r.name}[{k}]"
out["rotation_qubits_lowered"] = [names[q] for q in rot_qubits]
# native-level: crx qubits
nat_rot = [(i.operation.name, [names[qc.find_bit(q).index] for q in i.qubits], float(i.operation.params[0])) for i in qc.data if i.operation.name in ("crx", "rz", "p", "crz", "cp")]
out["native_rotations"] = nat_rot
print("rotation qubits (lowered):", out["rotation_qubits_lowered"]); print("native rotations:", nat_rot)
# distinct rotation angles & the data qubit they act on
angs = sorted({round(abs(a), 12) for a in lm["rz_angles"]}); out["rz_angles_abs_distinct"] = angs; print("distinct |angles|:", angs, "alpha_P=2beta=", 2 * beta)
# outer untouched: no gate on o[0..15] at all
oq = [qo.find_bit(q).index for q in qo.qregs[1]]
touched = sorted({qo.find_bit(q).index for i in qo.data for q in i.qubits} & set(oq))
out["outer_qubits_touched"] = touched; print("outer touched:", touched)
# same gate skeleton for different beta; only rotation angles differ
q2 = build_UB(0.4)
out["skeleton_same_for_beta"] = [i.operation.name for i in qc.data] == [i.operation.name for i in q2.data]
# T(eps)
rows = t_table(qc, (1e-4, 1e-6, 1e-8, 1e-10), qiskit=True)
for r in rows: print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
out["t_table"] = rows
# per-angle T
out["per_angle_T"] = {f"{e:g}": [pygridsynth_tcount(th, e) for th in lm["rz_angles"]] for e in (1e-4, 1e-6, 1e-8, 1e-10)}
# synthesis + sparse evaluation
V = enc.target("UB", None, beta)
res = {}
for eps in (1e-4, 1e-6):
    t0 = time.time(); synth, info = synthesize(qc, eps); tsyn = time.time() - t0
    tol = synth_tolerances(lm["n_rot"], eps)
    sm = logical_metrics(synth)
    # sparse engine alone, with a raised cap if needed, record peak stored amplitudes
    rec = dict(eps=eps, n_rot=info["n_rot"], t_rot=info["t_rot"], t_total=info["t_rot"] + lm["t_fixed"], t_gates_in_synth=synth.count_ops().get("t", 0) + synth.count_ops().get("tdg", 0),
               error_bound_sum=info["error_bound_sum"], tol=tol, synth_seconds=tsyn, synth_cx=synth.count_ops().get("cx", 0), synth_gates=sum(synth.count_ops().values()))
    for engine, cap in (("sparse", 5_000_000), ("auto", 5_000_000)):
        t0 = time.time()
        try:
            v = evaluate(synth, enc, V, engine=engine, cap=cap, **tol)
            rec[engine] = dict(ok=v.ok, reason=v.reason, engine_used=v.engine, certified=v.certified, op_norm_error=v.op_norm_error, block_error=v.block_error,
                               leak_amplitude=v.leak_amplitude, gauss=v.gauss_residual, max_leak=v.max_leak, dirty=v.dirty_ancilla, dropped_total=v.dropped_total,
                               engine_accuracy=v.engine_accuracy, method=v.method, seconds=v.seconds, wall=time.time() - t0, extra={k: (float(x) if isinstance(x, (int, float, np.floating)) else str(x)) for k, x in v.extra.items()})
        except Exception as e:
            rec[engine] = dict(exception=f"{type(e).__name__}: {str(e)[:200]}", wall=time.time() - t0)
        print(eps, engine, rec[engine], flush=True)
    # peak amplitudes with the plain sparse engine on the 625 inner codes (no outer) at several caps
    codes = enc.inner_codes(); peaks = {}
    for cap in (5_000_000, 20_000_000, 60_000_000):
        t0 = time.time()
        try:
            b = ss.run_batch(synth, codes, cap=cap); peaks[str(cap)] = dict(ok=True, stored_final=int(len(b.keys)), seconds=time.time() - t0)
            break
        except ss.SimCapExceeded: peaks[str(cap)] = dict(ok=False, seconds=time.time() - t0)
    rec["inner625_run_batch"] = peaks; print(peaks, flush=True)
    res[str(eps)] = rec
out["synth"] = res
out["maxrss_MB"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)
