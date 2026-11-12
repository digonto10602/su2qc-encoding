"""Tester 223 (rishon D3): det-layer cost numbers by my own count + production verdict.  (1) T count: 8 rotations rz(2 eta), eps = 1e-6 each,
word from pygridsynth called directly (letters H S T X W parsed by my own matrices; error recomputed), also the 20-eta set of prompts/204 section 5
(seed 20261110, uniform(0.05, 1.2)); mean/range.  (2) production verify(build_UD(eta), 'UD', eta=eta): op_norm_error, Gauss residual, certified,
method.  (3) depth of the CX/H/rz circuit and Qiskit count_ops.  Run: PYTHONPATH=src python this.  Output: results/rishon/tester-223-det-metrics.json"""
import json, math, subprocess, time
import numpy as np, mpmath
from pygridsynth.gridsynth import gridsynth_gates
import sys; sys.path.insert(0, "src")
from su2plaq.circuits import rishon as R
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as V
t00 = time.time()
Hm = np.array([[1, 1], [1, -1]]) / math.sqrt(2); Sm = np.diag([1, 1j]); Tm = np.diag([1, np.exp(1j * math.pi / 4)]); Xm = np.array([[0, 1], [1, 0]]); Wm = np.exp(1j * math.pi / 4) * np.eye(2)
L = {"H": Hm, "S": Sm, "T": Tm, "X": Xm, "W": Wm}
def word_mat(w):
    M = np.eye(2, dtype=complex)
    for ch in w: M = M @ L[ch]                        # string read left to right = matrix product left to right (circuit order = reversed; error is order-agnostic if I test both)
    return M
def err(w, th):
    tgt = np.diag([np.exp(-1j * th / 2), np.exp(1j * th / 2)])
    best = 9.0
    for A in (word_mat(w), word_mat(w[::-1])):
        ov = np.trace(tgt.conj().T @ A); ph = ov / abs(ov); best = min(best, float(np.linalg.norm(A - ph * tgt, 2)))
    return best
def tcount(theta, eps):
    w = str(gridsynth_gates(theta=mpmath.mpf(repr(theta)), epsilon=mpmath.mpf(repr(eps))))
    return w.count("T"), err(w, theta)
rec = {"nominal": {}, "verify": {}}
eps = 1e-6
for eta in (0.29, 0.53, 1.07):
    n, e = tcount(2 * eta, eps)
    rec["nominal"][str(eta)] = {"T_per_rotation": n, "word_error": e, "T_total_8_rotations": 8 * n}
    print(eta, n, e, 8 * n, flush=True)
ETA = np.random.default_rng(20261110).uniform(0.05, 1.2, 20)
tot = []
for eta in ETA:
    n, e = tcount(2 * float(eta), eps); tot.append(8 * n)
    assert e <= eps
rec["eta_set20"] = {"eta": ETA.tolist(), "T_det": tot, "mean": float(np.mean(tot)), "min": int(min(tot)), "max": int(max(tot)), "sum": int(sum(tot))}
print("eta set mean", np.mean(tot), min(tot), max(tot))
enc = RishonEncoding()
for eta in (0.29, 0.53, 1.07):
    qc = R.build_UD(eta)
    v = V.verify(qc, enc, "UD", None, None, eta=eta)
    from qiskit import transpile
    rec["verify"][str(eta)] = {"ok": v.ok, "certified": v.certified, "reason": v.reason, "method": v.method, "op_norm_error": v.op_norm_error, "block_error": v.block_error,
        "leak_amplitude": v.leak_amplitude, "dropped_total": v.dropped_total, "gauss_residual": v.gauss_residual, "gauss_states": v.gauss_states, "outer_bits_read": v.outer_bits_read,
        "depth": qc.depth(), "count_ops": {k: int(x) for k, x in qc.count_ops().items()}}
    print(eta, {k: rec["verify"][str(eta)][k] for k in ("ok", "certified", "op_norm_error", "gauss_residual", "depth")}, flush=True)
rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(); rec["t_total_s"] = time.time() - t00
json.dump(rec, open("results/rishon/tester-223-det-metrics.json", "w"), indent=1, default=str)
