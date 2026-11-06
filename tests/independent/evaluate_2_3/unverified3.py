import time, dataclasses, json
from su2plaq.circuits import twelve as C
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec
S0 = default_spec("twelve","step")
qc = C.build_step(0.37, 0.61, 1, with_outer=True)
out = {}
for tol in (8e-10, 1e-9):
    spec = dataclasses.replace(S0, support_cap=2000, tol_err=tol, tol_gauss=tol)
    t0 = time.time(); r = E.evaluate_circuit(qc, spec, "full"); v = r.verdict
    out[f"tol{tol}"] = dict(valid=r.valid, reason=r.reason, engine=v.engine, ok=v.ok, certified=v.certified, err=v.op_norm_error, acc=v.engine_accuracy, wall=round(time.time()-t0,1))
    print(out[f"tol{tol}"], flush=True)
json.dump(out, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/unverified3.json","w"), indent=1)
