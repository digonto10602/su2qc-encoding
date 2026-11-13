"""Tester 411: read-only spot check of results/rishon det-term JSONs. Run: python results/rishon/tester-411-spotcheck.py"""
import json, math, subprocess
out = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), "files": {}}
for f in ["UE","UB","UD","step","step_order2","step3","step3_order2"]:
    d = json.load(open(f"results/rishon/{f}.json"))
    v = d["verification"]; m = d["metrics"]
    rec = {"params": d["params"], "prov_commit": d["provenance"]["git_commit"], "dirty": d["provenance"]["git_dirty"],
           "ok": v.get("ok"), "certified": v.get("certified"), "reason": v.get("reason"),
           "op_norm_error": v.get("op_norm_error"), "block_error": v.get("block_error"),
           "leak": v.get("leak_amplitude"), "dropped": v.get("dropped_total"),
           "gauss_residual": v.get("gauss_residual"), "gauss_states": v.get("gauss_states"),
           "tol": v.get("tolerances"), "engine": v.get("engine"), "method": v.get("method"),
           "logical": m.get("logical"), "t_table": [(r["eps"], r.get("t_total"), r.get("n_rot")) for r in m.get("t_table",[])],
           "extra_keys": list(d.get("extra",{}).keys())}
    out["files"][f] = rec
json.dump(out, open("results/rishon/tester-411-spotcheck.json","w"), indent=1, default=str)
for f, r in out["files"].items():
    print(f, r["params"], r["prov_commit"], "dirty", r["dirty"])
    print("   ok", r["ok"], "cert", r["certified"], "op", r["op_norm_error"], "block", r["block_error"], "dropped", r["dropped"], "gauss", r["gauss_residual"], r["gauss_states"], "tol", r["tol"], r["engine"])
    print("   logical", r["logical"])
    print("   T", r["t_table"])
