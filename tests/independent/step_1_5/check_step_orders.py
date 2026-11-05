"""Tester step 1.5: build_step vs target(kind='step', order); wrong-order error sizes; order-2 gate-for-gate structure;
error_bound_sum semantics; logical_metrics + T(eps) tables.  Usage: PYTHONPATH=src python check_step_orders.py out.json"""
import sys, json, time, subprocess, warnings
import numpy as np
warnings.filterwarnings("ignore")
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_step, build_UE, build_UB
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.metrics.logical import logical_metrics
from su2plaq.metrics.cliffordt import synthesize, t_table

enc = TwelveQubit()
out = dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted")

def phase_opnorm(A, B):
    ov = np.trace(B.conj().T @ A); ph = ov / abs(ov)
    return float(np.linalg.norm(A - ph * B, 2))

# (1) build_step vs target
rows = []
for a, b in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
    for order in (1, 2):
        qc = build_step(a, b, order=order)
        t0 = time.time(); v = evaluate(qc, enc, enc.target("step", a, b, order=order)); dt = time.time() - t0
        rows.append(dict(alpha=a, beta=b, order=order, case="right", ok=v.ok, certified=v.certified, op_norm_error=v.op_norm_error, block=v.block_error,
                         leak=v.leak_amplitude, gauss=v.gauss_residual, max_leak=v.max_leak, dirty=v.dirty_ancilla, engine=v.engine, method=v.method, sec=dt))
        print(rows[-1])
    # wrong order: circuit order1 vs target order2
    v = evaluate(build_step(a, b, order=1), enc, enc.target("step", a, b, order=2))
    rows.append(dict(alpha=a, beta=b, order="c1_vs_t2", case="wrong", ok=v.ok, op_norm_error=v.op_norm_error, block=v.block_error)); print(rows[-1])
    v = evaluate(build_step(a, b, order=2), enc, enc.target("step", a, b, order=1))
    rows.append(dict(alpha=a, beta=b, order="c2_vs_t1", case="wrong", ok=v.ok, op_norm_error=v.op_norm_error, block=v.block_error)); print(rows[-1])
    # U_E U_B (swapped composition) as circuit
    ub = build_UB(b); sw = ub.copy_empty_like(name="sw"); sw.compose(ub, inplace=True); sw.compose(build_UE(a), qubits=list(range(12)), inplace=True)
    v = evaluate(sw, enc, enc.target("step", a, b, order=1))
    rows.append(dict(alpha=a, beta=b, order="UEUB_circuit_vs_t1", case="wrong", ok=v.ok, op_norm_error=v.op_norm_error, block=v.block_error, leak=v.leak_amplitude)); print(rows[-1])
    # target-level sizes
    t1 = enc.target("step", a, b, order=1); t2 = enc.target("step", a, b, order=2)
    UE = enc.target("UE", a, None); UB = enc.target("UB", None, b)
    rows.append(dict(alpha=a, beta=b, case="targets", t1_vs_t2=phase_opnorm(t1, t2), UBUE_vs_UEUB=phase_opnorm(UB @ UE, UE @ UB),
                     t1_is_UBUE=phase_opnorm(t1, UB @ UE), comm_norm_ab=float(np.linalg.norm(UB @ UE - UE @ UB, 2)))); print(rows[-1])
out["part1"] = rows

# (2) gate-for-gate
def flat(qc):
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits), tuple(round(float(p), 15) for p in i.operation.params)) for i in qc.data]
a, b = 0.37, 0.61
s2 = build_step(a, b, order=2)
ref = build_UB(b).copy_empty_like()
ref.compose(build_UE(a / 2), qubits=list(range(12)), inplace=True); ref.compose(build_UB(b), inplace=True); ref.compose(build_UE(a / 2), qubits=list(range(12)), inplace=True)
s1 = build_step(a, b, order=1)
ref1 = build_UB(b).copy_empty_like(); ref1.compose(build_UE(a), qubits=list(range(12)), inplace=True); ref1.compose(build_UB(b), inplace=True)
out["part2"] = dict(order2_equal=flat(s2) == flat(ref), order1_equal=flat(s1) == flat(ref1), n_gates_s2=len(s2.data), n_gates_s1=len(s1.data),
                    global_phase=(s2.global_phase, ref.global_phase, s1.global_phase, ref1.global_phase), n_UE=len(build_UE(a).data), n_UB=len(build_UB(b).data))
print(out["part2"])

# (4) error_bound_sum semantics
sem = []
for eps in (1e-4, 1e-6, 1e-8, 1e-10):
    sy, info = synthesize(build_step(a, b, order=2), eps)
    per = [p for p in info["per_rotation"] if not p["exact"]]
    sem.append(dict(eps=eps, n_rot=info["n_rot"], error_bound_sum=info["error_bound_sum"], n_rot_eps=info["n_rot"] * eps, eq=info["error_bound_sum"] == info["n_rot"] * eps,
                    sum_measured=float(sum(p["error"] for p in per)), max_measured=float(max(p["error"] for p in per)), n_nonexact_per=len(per)))
    print(sem[-1])
# float behaviour of the old running sum
old = {}
for eps in (1e-4, 1e-6, 1e-8, 1e-10):
    for n in (4, 6, 8, 10, 14, 16, 18, 24):
        s = 0.0
        for _ in range(n): s += eps
        old[f"{eps:g}/{n}"] = s <= n * eps
out["part4"] = dict(rows=sem, old_running_sum_le_n_eps=old, n_violations_old=sum(not v for v in old.values()), n_cases=len(old))
print("old running sum violates n*eps in", out["part4"]["n_violations_old"], "of", len(old))

# (5) logical_metrics + T table
t5 = {}
for order in (1, 2):
    qc = build_step(a, b, order=order)
    lm = logical_metrics(qc)
    rows = t_table(qc, (1e-4, 1e-6, 1e-8, 1e-10))
    t5[order] = dict(lm={k: lm[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits", "ancilla")}, gates=lm["gates"], table=rows)
    print(order, t5[order]["lm"]); [print("  ", r) for r in rows]
    qo = build_step(a, b, order=order, with_outer=True); lmo = logical_metrics(qo)
    t5[order]["lm_outer"] = {k: lmo[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits", "ancilla")}
    print("  with_outer", t5[order]["lm_outer"])
out["part5"] = t5
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
