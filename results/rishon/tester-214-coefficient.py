"""Tester 214: electric_coefficient() value, wiring and mutation sensitivity.  Run: PYTHONPATH=src python results/rishon/tester-214-coefficient.py"""
import json, subprocess
import numpy as np
from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import operators as O, results as R, algebra as AL

out = {"commit": subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip()}
enc = RishonEncoding()
alpha = 0.37
def snapshot():
    O._link.cache_clear(); O.electric_coefficient.cache_clear(); O._HE.cache_clear()
    c = O.electric_coefficient()
    he = O.h_electric_inner(); nq = O._n_quartet()
    ue = C.build_UE(alpha)
    ang = [i.operation.params[0] for i in ue.data if i.operation.name == "p"]
    row = C.build_UE(alpha, with_outer=True, include_outer_electric=True)
    cert = R.outer_electric_certify(row, enc, alpha)
    chk = R.outer_electric_check(row, enc, alpha, n_codes=300)
    return c, he, nq, ang, cert, chk, row
c, he, nq, ang, cert, chk, row0 = snapshot()
out["baseline"] = {"coef": c, "abs_dev_from_0.75": abs(c - 0.75), "h_el_minus_coef_nq": float(np.abs(he - c * nq).max()),
                   "p_angles_equal_minus_coef_alpha": [abs(a + c * alpha) for a in ang], "n_p": len(ang),
                   "certified": cert["certified"], "error_bound": cert["error_bound"], "check_max_error": chk["max_error"],
                   "target_label": cert["target"], "check_label": chk["target"]}
# mutation: quartet Casimir doubled (RishonLink subclass scaling the Casimirs)
class Mut(AL.RishonLink):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.casimir_L = 2 * self.casimir_L; self.casimir_R = 2 * self.casimir_R
orig = O.RishonLink; O.RishonLink = Mut
try:
    c2, he2, nq2, ang2, cert2, chk2, row2 = snapshot()
    out["mutant_casimir_x2"] = {"coef": c2, "h_el_minus_coef_nq": float(np.abs(he2 - c2 * nq2).max()), "h_el_max_ratio_to_baseline": float(he2.max() / he.max()),
        "p_angles_equal_minus_coef_alpha": [abs(a + c2 * alpha) for a in ang2],
        "certify_mutant_circuit_under_mutant": {"certified": cert2["certified"], "error_bound": cert2["error_bound"]},
        "certify_baseline_circuit_under_mutant": {k: v for k, v in R.outer_electric_certify(row0, enc, alpha).items() if k in ("certified", "error_bound")}}
    # a mutation that breaks the structure (nonzero on A): must be rejected by the assertions
    class Mut2(AL.RishonLink):
        def __init__(self, *a, **k):
            super().__init__(*a, **k); n = self.casimir_L.shape[0]; self.casimir_L = self.casimir_L + 0.3 * np.eye(n)
    O.RishonLink = Mut2; O._link.cache_clear(); O.electric_coefficient.cache_clear()
    try: O.electric_coefficient(); out["mutant_nonzero_on_AB"] = "NOT rejected"
    except AssertionError as e: out["mutant_nonzero_on_AB"] = f"AssertionError: {e}"
finally:
    O.RishonLink = orig; O._link.cache_clear(); O.electric_coefficient.cache_clear(); O._HE.cache_clear()
c3, *_ = snapshot()
out["restored_coef"] = c3
print(json.dumps(out, indent=1, default=str)); json.dump(out, open("results/rishon/tester-214-coefficient.json", "w"), indent=1, default=str)
