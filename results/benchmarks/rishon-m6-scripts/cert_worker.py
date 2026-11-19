"""usage: cert_worker.py <general|headline|det> <tree> <out_dir>   (fresh process per call; prints one JSON line)
Times the rishon Lean certificate (export + compiled checker) of the general step circuit (baselines.general_circuit, as
write_general_step_theorem), of the headline program compress/programs/rishon/F3/006-closed-mark-in-restore.py (round._certify =
section 6.4 angle-fit confirmation + certify_circuit) or of the det layer.  Breakdown by wrapping lean_cert functions (no source edits)."""
import sys, json, time, pathlib, os
what, tree, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
sys.path.insert(0, str(tree / "src"))
out.mkdir(parents=True, exist_ok=True)
t_imp = time.perf_counter()
from su2plaq.rishon import lean_cert as LC
from su2plaq.rishon.compress import baselines as BL, round as R
from su2plaq.rishon.compress.spec import rishon_spec
import su2plaq.rishon.lean_cert as LCmod
assert str(LCmod.__file__).startswith(str(tree)), LCmod.__file__
T = {}
def wrap(mod, name):
    f = getattr(mod, name)
    def g(*a, **k):
        t0 = time.perf_counter()
        try: return f(*a, **k)
        finally: T[name] = T.get(name, 0.0) + time.perf_counter() - t0
    setattr(mod, name, g)
for n in ("_export", "check_inner_certificate", "confirm_angle_fit", "_mismatch", "_run_checker", "exact_target"):
    wrap(LC, n)
spec = rishon_spec("step")
t_imp = time.perf_counter() - t_imp
t0 = time.perf_counter()
if what == "general":
    qc = BL.general_circuit(spec)
    t_build = time.perf_counter() - t0
    t0 = time.perf_counter()
    cert = LC.certify_circuit(qc, spec, out_dir=out)
    t_cert = time.perf_counter() - t0
    res = {"status": cert.status, "reason": cert.reason, "lean_seconds_field": cert.seconds}
elif what == "headline":
    prog = "compress/programs/rishon/F3/006-closed-mark-in-restore.py"
    qc, err = R._circuit_of(spec, prog, "x", None, tree)
    assert qc is not None, err
    t_build = time.perf_counter() - t0
    t0 = time.perf_counter()
    d, sec = R._certify(qc, spec, prog, tree)
    t_cert = time.perf_counter() - t0
    res = {"status": d.get("status"), "reason": d.get("reason"), "lean_seconds_field": d.get("seconds"), "round_certify_seconds": sec}
elif what == "det":
    from su2plaq.circuits import rishon as C
    from su2plaq.encodings.rishon import RISHON_NOMINAL_ETA
    qc = C.build_UD(RISHON_NOMINAL_ETA)
    t_build = time.perf_counter() - t0
    t0 = time.perf_counter()
    cert = LC.certify_det_layer(qc, RISHON_NOMINAL_ETA, out_dir=out)
    t_cert = time.perf_counter() - t0
    res = {"status": cert.status, "reason": cert.reason, "lean_seconds_field": cert.seconds}
res.update({"what": what, "import_s": t_imp, "build_circuit_s": t_build, "certify_total_s": t_cert, "n_gates": len(qc.data),
            "breakdown_s": T, "module_file": LC.__file__})
print("RESULT " + json.dumps(res))
