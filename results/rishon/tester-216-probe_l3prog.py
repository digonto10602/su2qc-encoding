import time
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL, round as RD
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress import baselines as LB
spec = rishon_spec("step")
fn = lambda s: BL.qiskit_l3(s, seed=12345)
t=time.time()
for name, make in (("laptop program_source fit (0,0),(1,0),(0,1)", lambda: fn), ("generic-pair linear fit", lambda: BL.linear_in_angles(fn, spec))):
    try:
        src = LB.program_source(make(), spec, summary="x"); print(name, "-> program OK, bytes", len(src), time.time()-t, flush=True)
    except ValueError as e:
        print(name, "-> ValueError:", str(e)[:200], time.time()-t, flush=True)
