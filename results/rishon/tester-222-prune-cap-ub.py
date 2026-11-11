"""Tester 222 D1 done-check: U_B rccx / mcx / ccx ladders under the rishon cap (numbers), plus an explicit physical-state cross-check."""
import json, subprocess, time
from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as RV
enc = RishonEncoding(); out = {}
for lad in ("ccx", "rccx", "mcx"):
    t = time.time(); qc = C.build_UB(0.61, ladder=lad)
    v = RV.verify(qc, enc, "UB", None, 0.61)
    x = RV.physical_cross_check(qc, enc, "UB", None, 0.61) if lad == "rccx" else None
    out[lad] = {"ok": v.ok, "reason": v.reason, "certified": v.certified, "dropped_total": v.dropped_total, "op_norm_error": v.op_norm_error,
                "block_error": v.block_error, "leak_amplitude": v.leak_amplitude, "gauss_residual": v.gauss_residual, "gauss_states": v.gauss_states,
                "shared_reason": v.inner_verdict.reason, "shared_ok": bool(v.inner_verdict.ok), "extra": {k: v.extra[k] for k in ("prune_fraction", "prune_cap", "laptop_reason")},
                "cx": qc.count_ops().get("cx", 0), "seconds": time.time() - t, "physical_cross_check": x}
    print(lad, out[lad], flush=True)
out["git"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
json.dump(out, open("results/rishon/tester-222-prune-cap-ub.json", "w"), indent=1, default=str)
