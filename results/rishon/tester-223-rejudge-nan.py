"""Tester 223: NaN / inf in the re-judge (verify._rejudge and verify.verify with a faked shared `pruning_bound` verdict).
In-process patch of su2plaq.rishon.verify.evaluate only (nothing in src/ edited).  Fields dropped_total, leak_amplitude, op_norm_error,
each in {nan, +inf, -inf}, plus pairs; and also NaN in every field of the SHARED non-pruning verdicts (passed through unchanged: record only).
Run: PYTHONPATH=src python this.  Output: results/rishon/tester-223-rejudge-nan.json"""
import dataclasses, json, subprocess, itertools
import numpy as np
from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.evaluate import evaluator as shared_ev
from su2plaq.rishon import verify as RV
enc = RishonEncoding(); qc = C.build_UE(0.37); real = shared_ev.evaluate
out = {"cases": [], "violations": []}
def run(label, **ov):
    def fake(*a, **k):
        return dataclasses.replace(real(*a, **k), ok=False, reason="pruning_bound", **ov)
    RV.evaluate = fake
    try:
        v = RV.verify(qc, enc, "UE", 0.37, None, 1)
    finally:
        RV.evaluate = real
    out["cases"].append({"case": label, "ok": bool(v.ok), "reason": v.reason, "failing": [(k, str(x)) for k, x in (v.failing_inputs or [])] if hasattr(v, "failing_inputs") else None})
    return v
bad = {"nan": float("nan"), "+inf": float("inf"), "-inf": float("-inf")}
# control
v = run("control: finite 5e-12", dropped_total=5e-12)
assert v.ok
for name, x in bad.items():
    for field, want in (("dropped_total", {"pruning_bound"}), ("leak_amplitude", {"leak", "dirty_ancilla"}), ("op_norm_error", {"error"})):
        base = {"dropped_total": 5e-12}; base[field] = x
        v = run(f"{field}={name}", **base)
        if field == "dropped_total" and name == "-inf":
            # -inf <= cap is True: a negative dropped total cannot exist; record, do not count as a violation if the other cascade stages hold
            out["cases"][-1]["note"] = "-inf dropped_total is impossible (a norm); recorded only"
            continue
        if v.ok or v.reason not in want:
            out["violations"].append(f"{field}={name}: ok={v.ok} reason={v.reason}")
# pairs
for a, b in itertools.product(("nan", "+inf"), repeat=2):
    v = run(f"leak={a},err={b}", dropped_total=5e-12, leak_amplitude=bad[a], op_norm_error=bad[b])
    if v.ok: out["violations"].append(f"pair {a},{b} accepted")
# direct _rejudge
from types import SimpleNamespace
for field in ("dropped_total", "leak_amplitude", "op_norm_error"):
    for name in ("nan", "+inf"):
        d = dict(dropped_total=1e-12, leak_amplitude=1e-13, op_norm_error=1e-12, dirty_ancilla=0.0, max_leak=0.0); d[field] = bad[name]
        r = RV._rejudge(SimpleNamespace(**d), RV.RISHON_PRUNE_FRACTION * 1e-10, 1e-10)
        out["cases"].append({"case": f"_rejudge direct {field}={name}", "reason": r[0]})
        if r[0] == "ok": out["violations"].append(f"_rejudge direct accepted {field}={name}")
r = RV._rejudge(SimpleNamespace(dropped_total=1e-12, leak_amplitude=1e-13, op_norm_error=1e-12, dirty_ancilla=0.0, max_leak=0.0), 1e-11, 1e-10)
out["cases"].append({"case": "_rejudge direct all finite", "reason": r[0]}); assert r[0] == "ok"
# boundary exactness: equality with the cap / tolerance is accepted (<=), as in the shared cascade
for field, val in (("dropped_total", 1e-11), ("leak_amplitude", 1e-10), ("op_norm_error", 1e-10)):
    d = dict(dropped_total=1e-12, leak_amplitude=1e-13, op_norm_error=1e-12, dirty_ancilla=0.0, max_leak=0.0); d[field] = val
    r = RV._rejudge(SimpleNamespace(**d), 1e-11, 1e-10)
    out["cases"].append({"case": f"boundary {field}={val:g} (equal to bound)", "reason": r[0]})
    if r[0] != "ok": out["violations"].append(f"boundary {field} equality rejected: {r[0]}")
out["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
json.dump(out, open("results/rishon/tester-223-rejudge-nan.json", "w"), indent=1)
print(len(out["cases"]), "cases;", "violations:", out["violations"])
