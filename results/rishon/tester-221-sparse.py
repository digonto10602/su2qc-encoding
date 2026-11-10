"""Tester 219: own sparse engine (tester-217-engine.py) on all 1296 inner codes x 3 spec angle pairs (+1 extra pair) for each round-1 archive
program, vs own dense targets (rishon.algebra + scipy expm).  Also skeleton independence and parameter linearity over 5 pairs.
usage: tester-221-sparse.py <cid> ; output results/rishon/tester-221-sparse-<cid>.json"""
import sys, time, json, subprocess, importlib.util, os, hashlib
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("c", os.path.join(here, "tester-221-common.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
eng = C.load_engine()
from su2plaq.rishon.compress.spec import rishon_spec
cid = sys.argv[1]
s0 = rishon_spec("step")
spec_pairs = [(s0.alpha, s0.beta)] + [tuple(p) for p in s0.alt_angles]
extra_pairs = [(2.6, -0.4), (0.13, 1.9)]
pairs = spec_pairs + extra_pairs
# ---- circuits, skeleton, linearity
circs = {p: C.build_circuit(cid, s0.with_angles(*p)) for p in pairs}
def skel(qc): return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
def par(qc): return [tuple(float(x) for x in i.operation.params) for i in qc.data]
sk0 = skel(circs[pairs[0]])
skel_equal = all(skel(circs[p]) == sk0 for p in pairs)
P = [np.array([x for t in par(circs[p]) for x in t]) for p in pairs]
lens_equal = len({len(x) for x in P}) == 1
A = np.array([[p[0], p[1]] for p in pairs]); Y = np.array(P)           # pairs x nparams
const_mask = (Y.max(0) - Y.min(0)) < 1e-14                               # parameters identical at all pairs (fixed angles, e.g. cp(-pi/2))
Yv = Y[:, ~const_mask]
coef, res, rk, sv = np.linalg.lstsq(A, Yv, rcond=None)
lin_resid = float(np.abs(A @ coef - Yv).max())
A1 = np.hstack([A, np.ones((len(pairs), 1))]); c1 = np.linalg.lstsq(A1, Yv, rcond=None)[0]
intercept_max = float(np.abs(c1[2]).max())
const_vals = sorted({round(float(v), 12) for v in Y[0, const_mask]})
n_const, n_var = int(const_mask.sum()), int((~const_mask).sum())
# coefficients (a_alpha, b_beta) of the varying parameters, in units of 1 and sqrt(2)
coef_set = sorted({(round(float(a), 9), round(float(b), 9)) for a, b in coef.T})
# which gates carry angle-dependent parameters (names)
names_param = {}
for gi, (nm, qs) in enumerate(sk0):
    npar = len(par(circs[pairs[0]])[gi])
    if npar: names_param[nm] = names_param.get(nm, 0) + 1
# fixed-param gates identical at all pairs?
fixed_ok = True
for gi in range(len(sk0)):
    vs = [par(circs[p])[gi] for p in pairs]
    if any(v != vs[0] for v in vs[1:]) and sk0[gi][0] not in ("rz", "p", "cp", "crx", "crz"):
        fixed_ok = False
out = dict(cid=cid, program_sha256=hashlib.sha256(open(C.program_path(cid), "rb").read()).hexdigest(), pairs=pairs, skeleton_equal_5_pairs=skel_equal,
           nparam_equal=lens_equal, n_params=int(Y.shape[1]), n_const_params=n_const, n_varying_params=n_var, const_values=const_vals, coefficient_set=coef_set, linearity_resid_max=lin_resid, intercept_max=intercept_max, angle_gate_counts=names_param,
           fixed_gates_unchanged=fixed_ok, rows=[])
print(cid, "skeleton equal (5 pairs)", skel_equal, "const params", n_const, const_vals, "varying", n_var, "linear resid %.2e intercept %.2e" % (lin_resid, intercept_max), names_param, "fixed ok", fixed_ok, flush=True)
targets = {}
for p in pairs[:4]:
    targets[p] = eng.algebra_targets(*p)
    T = targets[p]
    print("targets", p, "HE offdiag %.1e HB herm %.1e" % (T["he_offdiag"], T["hb_herm"]), "UB unitarity %.1e" % np.abs(T["UB"].conj().T @ T["UB"] - np.eye(1296)).max(), flush=True)
for p in pairs[:4]:
    qc = circs[p]
    ops = eng.lower(qc); qs = eng.used_qubits(ops); T = targets[p]
    t0 = time.time()
    sim = eng.Sim(T["codes"], qs, thr=1e-15); sim.run(ops)
    M, wd, wo = sim.block(T["codes"], list(range(16)))
    ph, e2, emax = eng.compare(M, T["step"])
    row = dict(alpha=p[0], beta=p[1], spec_pair=p in spec_pairs, n_gates=len(ops), n_qubits_total=qc.num_qubits, n_qubits_touched=len(qs),
               outer_touched=sorted(q for q in qs if 16 <= q < 48), ancillas_touched=sorted(q for q in qs if q >= 48),
               block_err_spectral=e2, block_err_maxabs=emax, leak_dirty_max=float(np.sqrt(wd.max())), leak_nocode_max=float(np.sqrt(wo.max())),
               leak_total_fro=float(np.sqrt((wd + wo).sum())), my_dropped_fro=float(np.sqrt(sim.dw_sq.sum())), my_dropped_triangle=float(np.sqrt((sim.dw_tri ** 2).sum())),
               max_state_size=int(sim.maxsize), phase_abs_minus_1=float(abs(ph) - 1), phase_angle=float(np.angle(ph)), seconds=time.time() - t0)
    out["rows"].append(row)
    print(cid, p, "err %.2e leak %.1e/%.1e dropped(fro) %.2e tri %.2e size %d outer %s  %.1fs" % (e2, row["leak_dirty_max"], row["leak_nocode_max"], row["my_dropped_fro"], row["my_dropped_triangle"], sim.maxsize, row["outer_touched"], row["seconds"]), flush=True)
out["commit"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
json.dump(out, open(os.path.join(here, f"tester-221-sparse-{cid}.json"), "w"), indent=1)
