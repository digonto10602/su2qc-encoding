"""Consistent (resealed) cache forgery -> archive -> gate re-evaluation (tester, 2.4 recheck)."""
import hashlib, json, pathlib, sys, tempfile
sys.path.insert(0, "src")
from su2plaq.compress import evaluate as E, archive as A
from su2plaq.compress.spec import default_spec
SCR = pathlib.Path(sys.argv[1]); BAD = SCR / "prog" / "002-bad.py"; SPEC = default_spec("twelve", "UE")
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)
def reseal(d): d["checksum"] = hashlib.sha256(canon({"meta": d["meta"], "payload": d["payload"]}).encode()).hexdigest(); return d
OUT = {}
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    rb = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root)
    (cf,) = list((root / "compress/cache").rglob("*.json")); d = json.loads(cf.read_text())
    good_metrics = dict(d["payload"]["metrics"]); OUT["honest_bad_result"] = dict(valid=rb.valid, reason=rb.reason, metrics_keys=sorted(good_metrics))
    p = d["payload"]; p["valid"] = True; p["reason"] = "ok"; p["skeleton_equal"] = True
    import copy; p["verdicts_alt"] = [copy.deepcopy(p["verdict"]) for _ in range(2)]   # the honest failed run has no alt verdicts
    for v in [p["verdict"]] + p["verdicts_alt"]: v["ok"] = True; v["certified"] = True
    p["metrics"].update(cx=0, t_eps=1, depth_ct=1, qubits=1)     # absurdly cheap
    cf.write_text(json.dumps(reseal(d)))
    r = E.evaluate_program(BAD, SPEC, "full", cache=True, root=root)
    OUT["forged_cache_returned"] = dict(valid=r.valid, reason=r.reason, n_alt=len(r.verdicts_alt), metrics={k: r.metrics[k] for k in ("cx", "t_eps", "depth_ct", "qubits")})
    arch = A.Archive.load("twelve", root=root, n_alt=len(SPEC.alt_angles))
    e = A.entry_from_result(r, program_path=str(BAD), family="F9", round=1, parent=None)
    OUT["entry"] = dict(key=list(e.key), cell=e.cell, valid=e.valid, skeleton=e.skeleton_equal, verdict_nominal_keys=sorted(e.verdict_nominal), alt=len(e.verdicts_alt))
    OUT["entry_problem"] = A.entry_problem(e, len(SPEC.alt_angles))
    ins = arch.insert(e); OUT["archive_insert_accepts"] = ins; OUT["archive_rejected"] = arch.rejected
    if ins:
        arch.save(); best = A.Archive.load("twelve", root=root, n_alt=2).best()
        fresh = E.evaluate_program(best.program_path, SPEC, "full", cache=False, root=root)
        OUT["gate"] = dict(fresh_valid=fresh.valid, fresh_reason=fresh.reason, recorded_key=list(best.key),
                           fresh_key=[fresh.metrics.get(k) for k in ("cx", "t_eps", "depth_ct", "qubits")] if fresh.metrics else None,
                           caught=(not fresh.valid))
print(json.dumps(OUT, indent=1, default=str))
json.dump(OUT, open("results/tester_m2_step2_4_recheck_forged_cache_gate.json", "w"), indent=1, default=str)
