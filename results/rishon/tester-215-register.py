"""Tester 215 probe (d): register() side effects on the laptop machinery; twelve general program evaluated after importing
su2plaq.rishon.compress equals results/compress/twelve/round-000.json general entry (key, verdict numbers)."""
import copy, json, subprocess, sys, types, pathlib, importlib
import numpy as np
def snap():
    out = {}
    for name, m in list(sys.modules.items()):
        if not name.startswith("su2plaq.") or "rishon" in name: continue
        for k, v in vars(m).items():
            if k.startswith("__"): continue
            if isinstance(v, (dict, set, list)):
                out[(name, k)] = repr(sorted(v, key=repr) if isinstance(v, set) else v)
    return out
import su2plaq.compress.evaluate, su2plaq.compress.spec, su2plaq.compress.builder, su2plaq.compress.provenance, su2plaq.encodings.base, su2plaq.evaluate.evaluator
import su2plaq.compress.oracle, su2plaq.compress.metrics, su2plaq.compress.archive, su2plaq.compress.round
before = snap()
h_before = su2plaq.compress.provenance.code_hash()
import su2plaq.rishon.compress as RC
after = snap()
changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
print("changed module-level containers outside rishon modules:", changed)
for k in changed:
    b, a = before.get(k), after.get(k)
    print(k, "\n   before:", (b or "")[:300], "\n   after :", (a or "")[:300])
import su2plaq.compress.evaluate as LE
print("ALLOWED_PROJECT_IMPORTS", sorted(LE.ALLOWED_PROJECT_IMPORTS), "FORBIDDEN_NAMES", sorted(LE.FORBIDDEN_NAMES))
print("laptop code_hash unchanged by import:", h_before == su2plaq.compress.provenance.code_hash(), h_before[:16])
r0 = json.load(open("results/compress/twelve/round-000.json"))
print("twelve round-000 evaluator_sha256", r0["evaluator_sha256"][:16], " current laptop code_hash", su2plaq.compress.provenance.code_hash()[:16])
from su2plaq.compress.spec import default_spec
from su2plaq.compress import baselines as LB
spec = default_spec("twelve", "step")
print("twelve spec sha", spec.sha256()[:16], "round-000 spec sha", r0["spec_sha256"][:16])
path = LB.general_program_path(spec)
import time; t = time.time()
r = LE.evaluate_program(str(path), spec, mode="full")
from su2plaq.compress.metrics import key
g = [c for c in r0["candidates"] if c["label"] == "general"][0]
print("valid", r.valid, r.reason, "key", list(key(r.metrics)), "stored", g["key"], "match", list(key(r.metrics)) == g["key"], "wall", time.time() - t)
print("err", r.verdict.op_norm_error, "stored", g["verdict"]["op_norm_error"], "gauss", r.verdict.gauss_residual, g["verdict"]["gauss_residual"], "prog sha eq", r.program_sha256 == g["program_sha256"])
print("t_measured", r.metrics["t_measured"], g["metrics"]["t_measured"], "depth", r.metrics["depth"], g["metrics"]["depth"])
res = dict(commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(), changed=[list(c) for c in changed],
           key=list(key(r.metrics)), stored_key=g["key"], key_equal=list(key(r.metrics)) == g["key"], program_sha_equal=r.program_sha256 == g["program_sha256"],
           laptop_code_hash_equal=h_before == su2plaq.compress.provenance.code_hash(), evaluator_sha_current_equals_round000=su2plaq.compress.provenance.code_hash() == r0["evaluator_sha256"])
json.dump(res, open("results/rishon/tester-215-register.json", "w"), indent=1)
