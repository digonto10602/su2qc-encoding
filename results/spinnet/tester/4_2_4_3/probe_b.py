"""Probe (b)/(c): angle-linearity of the qiskit_l3 seed, local baseline helpers vs the laptop's, whitelists."""
import sys, json, pathlib, numpy as np
from su2plaq.spinnet import loop as L
from su2plaq.compress import baselines as BL, evaluate as E, spec as S
root = pathlib.Path(sys.argv[1])
out = {}
sp = L.spec()
# --- (b1) qiskit_l3 seed program: angle-linear and genuinely a transpile of the reference at many generic pairs
f = root / "compress/programs/spinnet/seed/011-qiskit_l3.py"
ns = {}
exec(compile(f.read_text(), str(f), "exec"), ns)
from numpy.random import default_rng
rng = default_rng(20261106)
pairs = [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00)] + [tuple(rng.uniform(0.05, 2.0, 2)) for _ in range(8)]

def gl(qc):
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits), tuple(float(p) for p in i.operation.params)) for i in qc.data]

res = []
for a, b in pairs:
    s = sp.with_angles(a, b)
    prog = ns["build"](s).circuit()
    fresh = L._qiskit_l3(L._reference_circuit(s))
    gp, gf = gl(prog), gl(fresh)
    same_skel = [(n, q) for n, q, _ in gp] == [(n, q) for n, q, _ in gf]
    dang = max([abs(p1 - p2) for (n1, q1, ps1), (n2, q2, ps2) in zip(gp, gf) for p1, p2 in zip(ps1, ps2)] or [0.0]) if same_skel else None
    res.append({"alpha": a, "beta": b, "n_gates": len(gp), "same_skeleton_as_fresh_transpile": same_skel, "max_angle_diff_vs_fresh": dang})
out["qiskit_l3_vs_fresh_transpile"] = res
# homogeneity: program angles at (2a,2b) are twice those at (a,b); additivity
def angles(a, b):
    return np.array([p for _, _, ps in gl(ns["build"](sp.with_angles(a, b)).circuit()) for p in ps])
x, y, z = angles(0.3, 0.2), angles(0.6, 0.4), angles(0.9, 0.6)
out["linearity"] = {"max|A(2v)-2A(v)|": float(np.abs(y - 2 * x).max()), "max|A(3v)-3A(v)|": float(np.abs(z - 3 * x).max()), "n_angles": int(len(x))}
# does the program's rotation set equal the general program's rotation angles (up to merges)?
nrot = {"qiskit_l3_prog": int(len(angles(0.37, 0.61)))}
out["n_rot"] = nrot
# --- evaluator checks all three pairs for this seed
d = json.loads((root / "results/compress/spinnet/round-000.json").read_text())
c = [c for c in d["candidates"] if c["label"] == "qiskit_l3"][0]
out["qiskit_l3_record"] = {"alt_ok": c["alt_ok"], "skeleton_equal": c["skeleton_equal"], "valid": c["valid"], "mode": c["mode"]}
fb = json.loads((root / "results/compress/spinnet/feedback" / f"{c['id']}.json").read_text())
out["feedback_keys"] = sorted(fb)[:40]
for k in ("verdict_nominal", "verdicts_alt", "alt_verdicts"):
    if k in fb:
        v = fb[k]
        out[k] = ([{kk: vv.get(kk) for kk in ("ok", "op_norm_error", "alpha", "beta")} for vv in v] if isinstance(v, list)
                  else {kk: v.get(kk) for kk in ("ok", "op_norm_error")})
# --- (b2) local baseline helpers vs the laptop's on the twelve encoding
tw = S.default_spec("twelve", "step")
qc = BL.general_circuit(tw)
lap = BL.qiskit_l3(tw, seed=12345)
mine = L._qiskit_l3(qc, seed=12345)
out["l3_helper_equals_laptop_on_twelve"] = {"gates_equal": gl(lap) == gl(mine), "n_gates": len(gl(lap)), "global_phase": [float(lap.global_phase), float(mine.global_phase)]}
lapw = BL.qiskit_l3_whole(tw)
minew = L._qiskit_l3_whole(qc)
out["l3_whole_helper_equals_laptop_on_twelve"] = {"gates_equal": gl(lapw) == gl(minew), "n_gates": len(gl(lapw))}
# polish: loop._polished(s) = polish(reference, s)[0]; the laptop: general_polished(spec)[0] = polish(general_circuit, spec)[0]
from su2plaq.compress.passes import polish
out["polish_equal_on_twelve"] = gl(polish(qc, tw)[0]) == gl(BL.general_polished(tw)[0])
# the laptop L3 window constant is read from the laptop module, not copied
import inspect
out["window_const"] = BL.L3_WINDOW
# --- (c) whitelists
out["whitelists"] = {"ALLOWED_PROJECT_IMPORTS": sorted(E.ALLOWED_PROJECT_IMPORTS), "FORBIDDEN_NAMES": sorted(E.FORBIDDEN_NAMES)}
print(json.dumps(out, indent=1, default=str))
