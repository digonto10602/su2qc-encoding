import json, dataclasses, numpy as np
from su2plaq.spinnet import loop as L
sp = L.spec(); seed = L.import_seed(sp, "paulo15")
def ev(s, tag):
    r = L.evaluate_seed(sp, s, "trial"); v = r.verdict
    return {tag: {"valid": r.valid, "reason": r.reason, "err": float(v.op_norm_error), "leak": float(v.leak_amplitude)}}
out = {}
out |= ev(seed, "baseline")
out |= ev(dataclasses.replace(seed, gauge=np.ones(433)), "gauge_all_plus")
g = seed.gauge.copy(); g[np.flatnonzero(g < 0)[0]] = 1.0
out |= ev(dataclasses.replace(seed, gauge=g), "gauge_one_state_flipped")
qc = seed.qc.copy(); qc.x(0)
out |= ev(dataclasses.replace(seed, qc=qc), "extra_x_on_data0")
qc = seed.qc.copy(); qc.x(8)
out |= ev(dataclasses.replace(seed, qc=qc), "write_outer8")
# wrong beta declared
out |= ev(dataclasses.replace(seed, beta=0.06), "declared_beta_0.06")
# gauge minus codes on a shifted gauge (flip of everything)
out |= ev(dataclasses.replace(seed, gauge=-seed.gauge), "gauge_global_minus")
# step-kind v2 seeds must reject a nominal beta change
v2 = L.import_seed(sp, "spinnet_v2:pairs9")
r = L.evaluate_seed(sp, v2, "full"); out["pairs9_full"] = {"valid": r.valid, "reason": r.reason, "alt": [a.ok if hasattr(a,'ok') else a.get('ok') for a in r.alt_verdicts] if hasattr(r,'alt_verdicts') else None}
print(json.dumps(out, indent=1))
