import time, dataclasses, pathlib
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec
UE = dataclasses.replace(default_spec("twelve","UE"), eval_budget_s=30.0)
p = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/programs/x_dos_support_blowup.py")
for m in ("trial","full"):
    t0=time.time(); r=E.evaluate_program(p, UE, m)
    print(m, r.valid, r.reason, round(time.time()-t0,1), None if r.verdict is None else r.verdict.engine, r.message[:100], flush=True)
