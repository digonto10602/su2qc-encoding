"""Tester 409: wall time of the nominal full verification of the windowed Qiskit-L3 seed (rishon step, 9688 CX) with the 300 s budget lifted to 1800 s;
the replay judged it `eval_budget`.  Run: PYTHONPATH=src python this --out <json>"""
import json, sys, time, subprocess
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress import evaluate as E, baselines as BL
spec = rishon_spec("step")
qc = BL.qiskit_l3(spec, seed=12345)
print("built", qc.num_qubits, dict(qc.count_ops()), flush=True)
t = time.time(); v = E._one_verdict(qc, spec, "full", 1800.0); dt = time.time() - t
rec = {"wall_s": dt, "ok": v.ok, "certified": v.certified, "op_norm_error": v.op_norm_error, "dropped_total": v.dropped_total, "engine": v.engine,
       "git": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "seed": 12345}
print(rec); json.dump(rec, open(sys.argv[sys.argv.index("--out") + 1], "w"), indent=1)
