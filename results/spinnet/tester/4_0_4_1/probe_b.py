import sys, json, time, pathlib
from su2plaq.compress import spec as S, evaluate as E, baselines as BL, metrics as M
mode = sys.argv[1]   # plain | shim
if mode == "shim":
    from su2plaq.spinnet import loop; loop.install()
tw = S.default_spec("twelve", "step")
p = str(BL.general_program_path(tw))
t0 = time.time()
r = E.evaluate_program(p, tw, mode="full")
key = list(M.key(r.metrics))
d = json.load(open("results/compress/twelve/round-000.json"))
c = [x for x in d["candidates"] if x["label"] == "general"][0]
print(json.dumps({"mode": mode, "valid": r.valid, "reason": r.reason, "key": key, "committed_key": c["key"], "key_equal": key == c["key"],
  "sha256": r.program_sha256 if hasattr(r,"program_sha256") else None, "committed_sha": c["program_sha256"],
  "op_norm_error": r.verdict.op_norm_error, "committed_err": c["verdict"]["op_norm_error"], "skeleton_equal": r.skeleton_equal,
  "metrics_equal": {k: (r.metrics[k] == c["metrics"][k]) for k in ("cx","t_fixed","n_rot","t_eps","depth","depth_ct","qubits")}, "wall": time.time()-t0}))
