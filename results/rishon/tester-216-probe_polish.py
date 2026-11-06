import json, numpy as np
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress import evaluate as E
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.compress.metrics import metrics, key
from su2plaq.lean.rules import LEAN_RULES
out = {}
spec = rishon_spec("UE")
qc = BL.general_circuit(spec)
q = qc.copy()
d = q.qregs[0]
# inject redundancy: x x, tdg t pair, and two adjacent rz on a data qubit, plus h h
q.x(0); q.x(0)
q.t(1); q.tdg(1)
q.h(2); q.h(2)
q.rz(0.3, 3); q.rz(-0.3, 3)
k0 = key(metrics(q, spec, measured=False)); kref = key(metrics(qc, spec, measured=False))
pol, log = BL.polish(q, spec)
k1 = key(metrics(pol, spec, measured=False))
r = E.evaluate_circuit(pol, spec, mode="full")
out["UE_injected"] = {"log": log, "key_in": list(k0), "key_ref": list(kref), "key_out": list(k1), "strictly_better": k1<k0, "out_is_input": pol is q,
  "full_valid": r.valid, "full_reason": r.reason, "op_norm_error": r.verdict.op_norm_error, "log_rule_names": [l.split(":")[0].split()[0] for l in log],
  "rules_in_LEAN_RULES": all(l.split(":")[0].split()[0] in LEAN_RULES for l in log)}
# injected *invalid* extra gate: polish should not hide nor bless it
qb = qc.copy(); qb.rz(0.01, 0); qb.rz(0.02, 0)   # an extra rotation = wrong circuit; merge gives rz(0.03) still wrong
pol2, log2 = BL.polish(qb, spec)
r2 = E.evaluate_circuit(pol2, spec, mode="full")
out["UE_wrong_input"] = {"log": log2, "out_is_input": pol2 is qb, "full_valid_after": r2.valid, "reason": r2.reason}
# step general
sp = rishon_spec("step")
qs = BL.general_circuit(sp)
ps, ls = BL.polish(qs, sp)
out["step_general"] = {"log": ls, "out_is_input": ps is qs}
# idempotent / determinism
p3, l3 = BL.polish(pol, spec); out["idempotent_out_is_input"] = p3 is pol
p4, l4 = BL.polish(q, spec); out["deterministic"] = (str(l4)==str(log)) and key(metrics(p4,spec,measured=False))==k1
# general_polished
gp, gl = BL.general_polished(spec); out["general_polished_UE"] = {"log": gl}
print(json.dumps(out, indent=1, default=str))
