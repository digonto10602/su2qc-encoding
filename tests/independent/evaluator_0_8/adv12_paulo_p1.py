from common import *
from qiskit import qpy
qc = qpy.load(open("/home/digimonk/Projects/su2qc-encoding/refs/paulo/SU2_plaquette_jmax_half_CT.qpy","rb"))[0]
V = enc.target("UB", None, 1.0)
tol = dict(tol_err=2e-5, tol_leak=1e-9, tol_gauss=2e-5)
v = evaluate(qc, enc, V, engine="auto", **tol)
rec("M1-P1 conditions on Paulo QPY (new tolerances)", "ok, certified, acc<=1e-9, tolerances==tol, gauss<=2e-5", f"{fmt(v)} certified={v.certified} acc={v.engine_accuracy} gauss={v.gauss_residual:.3e} tolerances={v.tolerances}", "", v.ok and v.certified and v.engine_accuracy <= 1e-9 and v.tolerances == tol and v.gauss_residual <= 2e-5 and v.op_norm_error<=2e-5 and v.max_leak<=1e-9)
v2 = evaluate(qc, enc, V.conj().T, engine=v.engine, **tol)
rec("M1-P1 inverse rejected", "not ok, err>0.1", f"{v2.reason} {v2.op_norm_error:.3f}", "", (not v2.ok) and v2.op_norm_error > 0.1)
json.dump(RES, open(OUT+"p1.json","w"), indent=1)
