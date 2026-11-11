"""Tester 222 (rishon D1): mutation test of the re-judge cascade in su2plaq.rishon.verify.verify.

The shared `evaluate` (imported into su2plaq.rishon.verify as `evaluate`) is replaced, in THIS process only, by a function that returns a real
shared verdict with fields overwritten (dataclasses.replace).  Nothing in src/ is edited.  The question: can the rishon cascade ever
return ok=True when the shared verdict's reason is something other than `pruning_bound` (or when a `pruning_bound` verdict hides another failure)?
Run: PYTHONPATH=src python results/rishon/tester-222-rejudge-mutations.py
"""
import dataclasses, json, subprocess, sys, time
import numpy as np

from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.evaluate import evaluator as shared_ev
from su2plaq.rishon import verify as RV
from qiskit import QuantumCircuit

enc = RishonEncoding()
qc = C.build_UE(0.37)                       # 16 qubits, exact; fast
real = shared_ev.evaluate
alpha = 0.37
out = {"cases": [], "shared_PRUNE_FRACTION": shared_ev.PRUNE_FRACTION, "RISHON_PRUNE_FRACTION": RV.RISHON_PRUNE_FRACTION}

base_iv = None


def run(label, circuit, kind="UE", alpha_=alpha, **overrides):
    """Patch RV.evaluate to return the real shared verdict with `overrides`; call RV.verify; record."""
    def fake(*a, **k):
        iv = real(*a, **k)
        return dataclasses.replace(iv, **overrides) if overrides else iv
    RV.evaluate = fake
    try:
        v = RV.verify(circuit, enc, kind, alpha_, None, 1)
    finally:
        RV.evaluate = real
    rec = {"case": label, "overrides": {k: (float(x) if isinstance(x, (int, float, np.floating)) else x) for k, x in overrides.items()},
           "ok": bool(v.ok), "reason": v.reason, "laptop_reason": v.extra.get("laptop_reason"), "dropped_total": float(v.dropped_total),
           "gauss_residual": float(v.gauss_residual) if np.isfinite(v.gauss_residual) else None}
    out["cases"].append(rec)
    return v


def fail_if(cond, msg):
    if cond:
        out.setdefault("violations", []).append(msg)
        print("VIOLATION:", msg)


t = time.time()
# 0. unmodified (control)
v0 = run("control: real verdict", qc)
fail_if(not v0.ok, "control not ok")
cap = RV.RISHON_PRUNE_FRACTION * 1e-10      # 1e-11
# 1. every non-pruning shared failure reason, with tiny dropped_total: must stay rejected with the same reason
for reason in ("error", "leak", "dirty_ancilla", "gauss", "bad_layout", "writes_outer", "disallowed_gate", "unsimulable", "eval_budget", "weird_new_reason"):
    for dropped in (0.0, 1e-13, 5e-12):             # 5e-12: between shared (1e-12) and rishon (1e-11) cap -- impossible for the shared cascade, adversarial
        v = run(f"fake shared reason={reason} dropped={dropped:g}", qc, ok=False, reason=reason, dropped_total=dropped)
        fail_if(v.ok, f"ACCEPTED shared reason {reason!r} with dropped_total={dropped:g}")
        fail_if(v.reason != reason, f"reason changed {reason!r} -> {v.reason!r} (dropped {dropped:g})")
# 2. shared pruning_bound: re-judged
for dropped, want in ((5e-12, "ok"), (1.0e-11 * 0.999, "ok"), (1.0e-11 * 1.001, "pruning_bound"), (1e-9, "pruning_bound"), (0.5, "pruning_bound")):
    v = run(f"fake shared pruning_bound dropped={dropped:g}", qc, ok=False, reason="pruning_bound", dropped_total=dropped)
    fail_if(v.reason != want, f"pruning_bound dropped={dropped:g}: want {want}, got {v.reason}")
# 3. shared pruning_bound hiding another failure: leak amplitude > tol, op-norm error > tol, both
v = run("pruning_bound + leak_amplitude 1e-9 (ancilla-dominated)", qc, ok=False, reason="pruning_bound", dropped_total=5e-12,
        leak_amplitude=1e-9, max_leak=1e-18, dirty_ancilla=1e-18)
fail_if(v.ok or v.reason not in ("leak", "dirty_ancilla"), f"hidden leak accepted / wrong reason {v.reason}")
v = run("pruning_bound + leak_amplitude 1e-9 (invalid-code dominated)", qc, ok=False, reason="pruning_bound", dropped_total=5e-12,
        leak_amplitude=1e-9, max_leak=1e-18, dirty_ancilla=0.0)
fail_if(v.ok or v.reason not in ("leak", "dirty_ancilla"), f"hidden leak accepted / wrong reason {v.reason}")
v = run("pruning_bound + op_norm_error 2e-10", qc, ok=False, reason="pruning_bound", dropped_total=5e-12, op_norm_error=2e-10)
fail_if(v.ok or v.reason != "error", f"hidden error accepted / wrong reason {v.reason}")
v = run("pruning_bound + op_norm_error 1.0000001e-10", qc, ok=False, reason="pruning_bound", dropped_total=5e-12, op_norm_error=1.0000001e-10)
fail_if(v.ok or v.reason != "error", f"hidden error accepted at the tolerance edge: {v.reason}")
v = run("pruning_bound + op_norm_error 0.99e-10 (inside tol)", qc, ok=False, reason="pruning_bound", dropped_total=5e-12, op_norm_error=0.99e-10)
fail_if(not v.ok, f"valid re-judge rejected: {v.reason}")
v = run("pruning_bound + NaN dropped_total", qc, ok=False, reason="pruning_bound", dropped_total=float("nan"))
fail_if(v.ok, "NaN dropped_total accepted")
v = run("pruning_bound + NaN op_norm_error", qc, ok=False, reason="pruning_bound", dropped_total=5e-12, op_norm_error=float("nan"))
fail_if(v.ok, "NaN op_norm_error accepted")
v = run("pruning_bound + NaN leak_amplitude", qc, ok=False, reason="pruning_bound", dropped_total=5e-12, leak_amplitude=float("nan"))
fail_if(v.ok, "NaN leak_amplitude accepted")
v = run("pruning_bound + inf op_norm_error", qc, ok=False, reason="pruning_bound", dropped_total=5e-12, op_norm_error=float("inf"))
fail_if(v.ok, "inf op_norm_error accepted")
# 4. after the re-judge says ok, the Gauss sample still decides: a circuit that is NOT Gauss-invariant, shared verdict faked 'pruning_bound' + clean numbers
bad = qc.copy()
bad.rx(0.7, 1)                         # leaves the physical subspace
v = run("Gauss: circuit with rx on d[1], faked clean pruning_bound", bad, ok=False, reason="pruning_bound", dropped_total=5e-12,
        op_norm_error=1e-13, leak_amplitude=0.0, block_error=1e-13)
fail_if(v.ok, "Gauss-violating circuit accepted through the re-judge")
out["gauss_case_reason"] = v.reason
# 5. real (unfaked) wrong circuit is still rejected
v = run("real wrong circuit (rx 0.7)", bad)
fail_if(v.ok, "real wrong circuit accepted")
# 6. prune_fraction below shared -> ValueError ; equal to shared allowed; the constant is looser
for frac, expect_err in ((1e-3, True), (9.99e-3, True), (1e-2, False), (1e-1, False), (0.5, False)):
    try:
        RV.verify(qc, enc, "UE", alpha, None, 1, prune_fraction=frac)
        got = False
    except ValueError:
        got = True
    out["cases"].append({"case": f"prune_fraction={frac}", "ValueError": got})
    fail_if(got != expect_err, f"prune_fraction={frac}: ValueError={got}, expected {expect_err}")
# 7. prune_fraction override of the cap: dropped 5e-12 with prune_fraction=1e-2 (cap 1e-12) -> pruning_bound
v = (lambda: (setattr(RV, "evaluate", lambda *a, **k: dataclasses.replace(real(*a, **k), ok=False, reason="pruning_bound", dropped_total=5e-12)),
              RV.verify(qc, enc, "UE", alpha, None, 1, prune_fraction=1e-2))[1])()
RV.evaluate = real
out["cases"].append({"case": "prune_fraction=1e-2 + dropped 5e-12", "reason": v.reason, "ok": bool(v.ok), "extra_prune_cap": v.extra.get("prune_cap")})
fail_if(v.reason != "pruning_bound", "explicit prune_fraction=1e-2 not honoured")
# 8. extra fields
v = run("extra fields", qc, ok=False, reason="pruning_bound", dropped_total=5e-12)
out["extra_keys"] = {k: v.extra.get(k) for k in ("prune_fraction", "prune_cap", "laptop_reason")}
out["inner_verdict_untouched"] = {"reason": v.inner_verdict.reason, "ok": bool(v.inner_verdict.ok), "dropped_total": float(v.inner_verdict.dropped_total)}
fail_if(v.inner_verdict.reason != "pruning_bound" or v.inner_verdict.ok, "inner_verdict not the untouched shared verdict")
# 9. module state: the shared constant untouched
out["shared_PRUNE_FRACTION_after"] = shared_ev.PRUNE_FRACTION
fail_if(shared_ev.PRUNE_FRACTION != 1e-2, "shared PRUNE_FRACTION changed")
fail_if(RV.evaluate is not real, "RV.evaluate not restored")
out["n_cases"] = len(out["cases"])
out["violations"] = out.get("violations", [])
out["wall_s"] = time.time() - t
out["git"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
json.dump(out, open("results/rishon/tester-222-rejudge-mutations.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("n_cases", "violations", "wall_s", "gauss_case_reason", "extra_keys", "inner_verdict_untouched")}, indent=1))
for c in out["cases"]:
    print(c)
