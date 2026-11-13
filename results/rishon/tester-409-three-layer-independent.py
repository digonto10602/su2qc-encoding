"""Tester 409 (rishon C1): independent check of three_layer.verify_three_layer's claims for the robust headline r04-F1-004.
Own JW link algebra (as tester-223) -> own 1296-dim U_B, U_D, U_E; target T = U_B(beta) U_D(eta) U_E(alpha) (first-order three-layer step, prompts/204 2.1).
Production is used only to BUILD the unit (E._build_in_subprocess on the program file) and to prepend the det layer; the full circuit is simulated by my
own sparse simulator using qiskit Operator matrices for every gate (so rccx/ccz/ch/crx phases are not hand-typed).  Inputs: 60 seeded random inner codes (+ 4 forced)
per triple.  Also: CX counts from count_ops; det-layer T count by own pygridsynth call (8 x rz(2 eta), eps 1e-6) and the 20-eta set mean.
Run: PYTHONPATH=src python this --out <json>"""
import itertools, json, pathlib, subprocess, sys, time
import numpy as np
from qiskit.quantum_info import Operator
t00 = time.time()
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1: M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
Uop = lambda i, j: c[i] @ cd[2 + j]
detU = Uop(0, 0) @ Uop(1, 1) - Uop(0, 1) @ Uop(1, 0); HDl = detU + detU.T
res_ = lambda M: M[np.ix_(SECTOR, SECTOR)]
Ub = [[res_(Uop(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Ub[i][j].T for j in range(2)] for i in range(2)]
def kron4(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]]) for a, b, cc, d in itertools.product(range(2), repeat=4)); HB = -(W + W.T)
hd = res_(HDl); HD = sum(kron4([hd if l == k else np.eye(6) for l in range(4)]) for k in range(4))
cas = np.array([0, .75, .75, .75, .75, 0.]); HE = np.array([sum(cas[(i // 6 ** l) % 6] for l in range(4)) for i in range(1296)])
wB, VB = np.linalg.eigh(HB); wD, VD = np.linalg.eigh(HD)
UBf = lambda b: (VB * np.exp(-1j * b * wB)) @ VB.T; UDf = lambda e: (VD * np.exp(-1j * e * wD)) @ VD.T; UEf = lambda a: np.diag(np.exp(-1j * a * HE))
codes = np.array(sorted(sum(SECTOR[s] << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(range(6), repeat=4)), dtype=np.int64)
# NOTE: my row-major index (link 0 least significant, sector index base 6) vs sorted codes: build an explicit map
idx6 = lambda cfg: sum(s * 6 ** l for l, s in enumerate(cfg))
code_of6 = np.zeros(1296, dtype=np.int64)
for cfg in itertools.product(range(6), repeat=4):
    code_of6[idx6(cfg)] = sum(SECTOR[s] << (4 * l) for l, s in enumerate(cfg))
pos6 = {int(cc): i for i, cc in enumerate(code_of6)}

_cache = {}
def gmat(op):
    key = (op.name, tuple(round(float(p), 15) for p in op.params))
    if key not in _cache: _cache[key] = Operator(op).data
    return _cache[key]
def merge(idx, amp):
    o = np.argsort(idx, kind="stable"); idx = idx[o]; amp = amp[o]
    first = np.concatenate(([True], idx[1:] != idx[:-1])); st = np.flatnonzero(first)
    a = np.add.reduceat(amp, st); ii = idx[st]; keep = np.abs(a) > 1e-16
    return ii[keep], a[keep]
def run(qc, start, pre):
    idx = np.array([start], dtype=np.int64); amp = np.array([1.0 + 0j])
    for (U, q) in pre:
        k = len(q); loc = np.zeros(len(idx), dtype=np.int64); mask = np.int64(0)
        for i, qq in enumerate(q): loc |= ((idx >> qq) & 1) << i; mask |= np.int64(1) << qq
        base = idx & ~mask; outs_i, outs_a = [], []
        for o in range(1 << k):
            coef = U[o, loc]; nz = np.abs(coef) > 1e-17
            if not nz.any(): continue
            ob = np.int64(0)
            for i, qq in enumerate(q): ob |= np.int64((o >> i) & 1) << qq
            outs_i.append(base[nz] | ob); outs_a.append(coef[nz] * amp[nz])
        idx, amp = merge(np.concatenate(outs_i), np.concatenate(outs_a))
    return idx, amp
def prep(qc):
    out = []
    for ins in qc.data:
        if ins.operation.name == "barrier": continue
        out.append((gmat(ins.operation), [qc.find_bit(x).index for x in ins.qubits]))
    return out, qc.global_phase
def columns(qc, inputs):
    pre, gp = prep(qc); C = []; leak = []
    for i in inputs:
        idx, amp = run(qc, int(code_of6[i]), pre); amp = amp * np.exp(1j * gp)
        col = np.zeros(1296, complex); lk = 0.0
        for a_, b_ in zip(idx, amp):
            if (int(a_) >> 16) == 0 and int(a_) in pos6: col[pos6[int(a_)]] = b_
            else: lk += abs(b_) ** 2
        C.append(col); leak.append(np.sqrt(lk))
    return np.array(C).T, max(leak)
if __name__ == "__main__":
    out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    entry = "r04-F1-004"; prog = "compress/programs/rishon/F1/004-pz-selector-walsh6.py"
    from su2plaq.rishon.compress.spec import rishon_spec
    from su2plaq.rishon.compress import evaluate as E
    from su2plaq.circuits.rishon import prepend_det_layer
    src = pathlib.Path(prog).read_bytes()
    spec = rishon_spec("step")
    triples = ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))
    units, _ = E._build_in_subprocess(src, [spec.with_angles(a, b) for a, b, _ in triples], E.BUILD_TIMEOUT_S)
    rng = np.random.default_rng(20261110)
    inputs = sorted(set(int(x) for x in rng.choice(1296, 60, replace=False)) | {0, 1295, 7, 777})
    rec = {"entry": entry, "program": prog, "n_inputs": len(inputs), "seed": 20261110, "triples": []}
    for (a, b, e), unit in zip(triples, units):
        full = prepend_det_layer(unit, e)
        T = (UBf(b) @ UDf(e) @ UEf(a))[:, inputs]
        Tunit = (UBf(b) @ UEf(a))[:, inputs]; Twrong = (UDf(e) @ UBf(b) @ UEf(a))[:, inputs]
        t0 = time.time(); C, lk = columns(full, inputs)
        ph = np.vdot(T, C); ph /= abs(ph)
        errcol = np.linalg.norm(C - ph * T, axis=0)
        # also: per-column phases may differ for an exact circuit only if the circuit is not a single unitary; use ONE global phase (above)
        phu = np.vdot(Tunit, C); phu /= abs(phu); phw = np.vdot(Twrong, C); phw /= abs(phw)
        ou, of = dict(unit.count_ops()), dict(full.count_ops())
        r = {"triple": [a, b, e], "max_col_err_vs_own_UB_UD_UE": float(errcol.max()), "max_abs_entry_err": float(np.abs(C - ph * T).max()), "max_leak_out_of_code_space": float(lk),
             "dist_to_unit_only_target": float(np.linalg.norm(C - phu * Tunit, axis=0).max()), "dist_to_wrong_order_UD_UB_UE": float(np.linalg.norm(C - phw * Twrong, axis=0).max()),
             "cx_unit": ou.get("cx", 0), "cx_full": of.get("cx", 0), "cx_added": of.get("cx", 0) - ou.get("cx", 0),
             "rz_added": of.get("rz", 0) - ou.get("rz", 0), "n_qubits": full.num_qubits, "t_sim_s": time.time() - t0}
        rec["triples"].append(r); print(r, flush=True)
    # det-layer T by own gridsynth
    import math, mpmath
    from pygridsynth.gridsynth import gridsynth_gates
    def tcount(th, eps=1e-6):
        w = str(gridsynth_gates(theta=mpmath.mpf(repr(th)), epsilon=mpmath.mpf(repr(eps)))); return w.count("T")
    rec["det_T_nominal"] = {str(e): 8 * tcount(2 * e) for _, _, e in triples}
    ETA = np.random.default_rng(20261110).uniform(0.05, 1.2, 20)
    ts = [8 * tcount(2 * float(x)) for x in ETA]; rec["det_T_eta_set_mean"] = float(np.mean(ts)); rec["det_T_eta_set"] = ts
    rec["unit_T_mean_from_robust_json"] = 843.8; rec["three_layer_T_mean_own"] = 843.8 + rec["det_T_eta_set_mean"]
    rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(); rec["t_total_s"] = time.time() - t00
    out.write_text(json.dumps(rec, indent=1) + "\n"); print("done", rec["det_T_nominal"], rec["det_T_eta_set_mean"], rec["three_layer_T_mean_own"], rec["t_total_s"])
