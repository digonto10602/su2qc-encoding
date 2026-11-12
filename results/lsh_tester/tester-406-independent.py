"""Tester 406: independent checks of the LSH L3 certificate export (seed-free; deterministic).
Run: taskset -c 14-19 tools/run-capped python results/lsh_tester/tester-406-independent.py"""
import json, time, sys, pathlib, subprocess
import numpy as np
from scipy.linalg import expm
sys.path.insert(0, "src")
from su2plaq.encodings.lsh import LSH
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.circuits import lsh as CL
from su2plaq.lsh import lean_export as LE

out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()}
enc = LSH()
n = len(enc.labels)
HB = enc.h_magnetic(); HE = enc.h_electric()
# ---- (a) my own electric weight: 3/4 * (# inner links with j=1/2) from the spin-network labels (different route)
sn = SpinNet()
print("labels equal to spinnet:", [str(a) for a in enc.labels[:2]], [str(a) for a in sn.labels[:2]])
HEs = sn.h_electric()
out["HE_lsh_vs_spinnet"] = float(np.abs(np.diag(HE) - np.diag(HEs)).max()) if HE.ndim == 2 else None
print("HE diag lsh vs spinnet", out["HE_lsh_vs_spinnet"], "offdiag", float(np.abs(HE - np.diag(np.diag(HE))).max()))
# ---- (b) my own Laurent evaluation vs dense expm (not enc.target), at 6 angle pairs
rng = np.random.default_rng(406)
pairs = [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00)] + [tuple(rng.uniform(-3, 3, 2)) for _ in range(3)]
res = {}
for kind, order in [("UE", 1), ("UB", 1), ("step", 1), ("step", 2)]:
    for (a, b) in pairs:
        V = LE.laurent_target_matrix(enc, kind, a, b, order)
        UE = lambda x: expm(-1j * x * HE) if HE.ndim == 2 else np.diag(np.exp(-1j * x * HE))
        UB = expm(-1j * b * HB)
        ref = {"UE": UE(a), "UB": UB, "step": UB @ UE(a) if order == 1 else UE(a / 2) @ UB @ UE(a / 2)}[kind]
        e_mine = float(np.abs(V - ref).max())
        e_enc = float(np.abs(V - enc.target(kind, a, b, order)).max())
        unit = float(np.abs(V.conj().T @ V - np.eye(n)).max())
        res[f"{kind}:{order}:{a:.4f},{b:.4f}"] = {"vs_expm": e_mine, "vs_enc_target": e_enc, "unitarity": unit}
        print(f"{kind} o{order} ({a:.3f},{b:.3f}) vs own expm {e_mine:.2e}  vs enc.target {e_enc:.2e}  unitarity {unit:.2e}")
out["laurent"] = res
# spectrum of H_B, projector construction independent
w = np.linalg.eigvalsh(HB)
out["HB_spectrum_unique"] = sorted(set(np.round(w, 9).tolist()))
print("HB spectrum", out["HB_spectrum_unique"])
# ---- (c) exact electric weight vs Python-rational count from labels of spinnet
nel = LE._n_inner_half(enc)
print("n_inner_half range", min(nel), max(nel), "3/4*n == diag(HE):", float(np.abs(0.75 * np.array(nel) - np.diag(HE)).max()))
# ---- (d) base
out["bases"] = {f"{k}:{o}": LE.target_base(k, o) for k, o in LE.LSH_TARGETS}
print(out["bases"])
# ---- (e) certify the circuits, times
cert = {}
al, be = 0.37, 0.61
cases = {
 "UE_o1": (CL.build_UE(al, True), "UE", 1),
 "UB_o1": (CL.build_UB(be, True), "UB", 1),
 "step_o1": (CL.build_step(al, be, 1, True), "step", 1),
 "step_o2": (CL.build_step(al, be, 2, True), "step", 2),
}
import tempfile
td = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "scratch/tester406certs"); td.mkdir(parents=True, exist_ok=True)
for name, (qc, kind, order) in cases.items():
    t0 = time.time(); r = LE.certify(qc, enc, kind, al, be, order, out_dir=td); dt = time.time() - t0
    cert[name] = {k: r[k] for k in ("status", "reason", "seconds", "check_seconds") if k in r} | {"wall": dt, "cx": qc.count_ops().get("cx", 0), "nq": qc.num_qubits}
    print(name, cert[name])
# wrong target kinds / -beta / eps / wrong order
neg = {}
def tryc(name, qc, kind, order, a=al, b=be):
    r = LE.certify(qc, enc, kind, a, b, order, out_dir=td)
    neg[name] = {"status": r["status"], "reason": r["reason"][:120]}
    print("NEG", name, neg[name])
tryc("UB_circuit_vs_step_target", CL.build_UB(be, True), "step", 1)
tryc("UB(-beta)_vs_UB", CL.build_UB(-be, True), "UB", 1)
tryc("step(-beta)_vs_step", CL.build_step(al, -be, 1, True), "step", 1)
tryc("step_beta(1+1e-6)", CL.build_step(al, be * (1 + 1e-6), 1, True), "step", 1)
tryc("step_alpha(1+1e-6)", CL.build_step(al * (1 + 1e-6), be, 1, True), "step", 1)
tryc("step_o1_circuit_vs_o2_target", CL.build_step(al, be, 1, True), "step", 2)
tryc("step_o2_circuit_vs_o1_target", CL.build_step(al, be, 2, True), "step", 1)
tryc("UE_circuit_vs_UB_target", CL.build_UE(al, True), "UB", 1)
tryc("step_wrong_alpha", CL.build_step(0.38, be, 1, True), "step", 1)
out["certs"] = cert; out["neg"] = neg
json.dump(out, open("results/lsh_tester/tester-406-independent.json", "w"), indent=1, default=str)
