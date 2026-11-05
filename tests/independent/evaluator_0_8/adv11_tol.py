from common import *
from su2plaq.evaluate.evaluator import synth_tolerances, TOL_GAUSS
VE = target(basis, "UE", alpha=alpha)
# synth_tolerances vs prompts/003 §2
for n, e in ((14, 1e-6), (4, 1e-6), (18, 1e-6), (16, 1e-4), (0, 1e-6)):
    exp = {"tol_err": n*e + 1e-9, "tol_leak": (n*e)**2 + 1e-12, "tol_gauss": n*e + 1e-9}
    got = synth_tolerances(n, e)
    rec(f"synth_tolerances({n},{e})", exp, got, "exact", got == exp and list(got) == ["tol_err", "tol_leak", "tol_gauss"])
rec("TOL_GAUSS default", 1e-10, TOL_GAUSS, "", TOL_GAUSS == 1e-10)
# early-exit tolerances
def early(label, qc, kw=None, expect=None):
    v = evaluate(qc, enc, I, **(kw or {}))
    rec(f"early exit {label}: tolerances recorded", expect, v.tolerances, "", (not v.ok) and v.tolerances == expect, "reason " + v.reason)
dflt = dict(tol_err=1e-10, tol_leak=1e-12, tol_gauss=1e-10)
qc, r = circ(True); qc.cx(r["d"][0], r["o"][0]); early("writes_outer default", qc, None, dflt)
early("writes_outer custom", qc, dict(tol_err=3e-5, tol_leak=2e-9, tol_gauss=7e-6), dict(tol_err=3e-5, tol_leak=2e-9, tol_gauss=7e-6))
qc = QuantumCircuit(16); qc.mcx([0,1,2], 3); early("disallowed_gate, tol_gauss None", qc, dict(tol_err=1e-6), dict(tol_err=1e-6, tol_leak=1e-12, tol_gauss=1e-10))
qc, r = circ(True); qc.p(0.3, r["o"][1]); early("unsimulable", qc, dict(engine="sparse", cap=10), dflt)
# ok verdict records tolerances
qc, r = circ(); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]
v = evaluate(qc, enc, VE); rec("ok verdict tolerances default", dflt, v.tolerances, "", v.tolerances == dflt and v.certified)
v = evaluate(qc, enc, VE, tol_gauss=3e-7); rec("tol_gauss override recorded", 3e-7, v.tolerances["tol_gauss"], "", v.tolerances["tol_gauss"] == 3e-7)
# Gauss reason uses effective tol_gauss
for eps in (2e-8, 2e-9):
    qc, r = circ(True); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]; qc.p(0.0, r["o"][1]); qc.crx(eps, r["d"][2], r["d"][1])
    d = evaluate(qc, enc, VE)
    lo = evaluate(qc, enc, VE, tol_gauss=10*eps)
    hi = evaluate(qc, enc, VE, tol_gauss=eps/10)
    edge = evaluate(qc, enc, VE, tol_gauss=d.gauss_residual*(1+1e-6)); edge2 = evaluate(qc, enc, VE, tol_gauss=d.gauss_residual*(1-1e-6))
    rec(f"gauss reason uses effective tol: crx({eps}) residual {d.gauss_residual:.3e}", "default fail(gauss), loose pass, tighter fail, edge: pass at r(1+1e-6), fail at r(1-1e-6)",
        f"default {d.reason}; tol {10*eps:g}: {lo.reason}; tol {eps/10:g}: {hi.reason}; edge {edge.reason}/{edge2.reason}; err {d.op_norm_error:.1e}; failing {d.failing_inputs[:1]}",
        "", d.reason == "gauss" and lo.ok and hi.reason == "gauss" and edge.ok and edge2.reason == "gauss")
# gauss failing_inputs use effective value
qc2, r2 = circ(True); qc2.p(0.0, r2["o"][1]); qc2.crx(2e-8, r2["d"][2], r2["d"][1])
# certified formula
qc, r = circ(); [qc.p(-0.75*alpha, r["d"][q]) for q in (2,5,8,11)]
cases = [("tol 1e-9/1e-9, gauss default 1e-10", dict(tol_err=1e-9, tol_leak=1e-9), False),
         ("tol 1e-9 x3", dict(tol_err=1e-9, tol_leak=1e-9, tol_gauss=1e-9), True),
         ("tol 1e-9 x2, gauss=False (gauss tol default ignored)", dict(tol_err=1e-9, tol_leak=1e-9, gauss=False), True),
         ("default tols", dict(), False),
         ("synth(14,1e-6)", synth_tolerances(14, 1e-6), False),
         ("synth(18,1e-6)", synth_tolerances(18, 1e-6), True),
         ("synth(4,1e-6)", synth_tolerances(4, 1e-6), False),
         ("P1 tol dict 2e-5/1e-9/2e-5", dict(tol_err=2e-5, tol_leak=1e-9, tol_gauss=2e-5), True)]
for nm, kw, exp in cases:
    v = evaluate(qc, enc, VE, engine="aer_mps", **kw)
    rec(f"aer_mps certified: {nm}", exp, f"certified={v.certified} ok={v.ok} acc={v.engine_accuracy}", "", v.certified == exp and v.ok)
    if nm.startswith("default"): pass
v = evaluate(qc, enc, VE, engine="sparse", **synth_tolerances(14, 1e-6)); rec("sparse certified at synth(14,1e-6)", True, v.certified, "", v.certified and v.ok)
json.dump(RES, open(OUT + "tol.json", "w"), indent=1)
