"""Tester 223 (rishon D3): three-layer step circuits build_step(..., order, eta) against my own composition, plus Trotter slopes.
Own pieces: JW link algebra -> own H_E, H_B, H_D^in on the 1296 inner codes (as tester-222-det-independent.py), own U_B U_D U_E compositions
(eigh), and my OWN sparse statevector simulator (index/amplitude arrays; gates x, z, p, rz, cx, cz, ccx, h, ch, crx; nothing from
su2plaq.evaluate).  Production is used only to build the circuits.  Inputs: |vac_A> and 40 seeded random valid inner codes (seed 20261110);
all ancillas start in |0>.  Run: PYTHONPATH=src python this.  Output: results/rishon/tester-223-step-orders.json"""
import itertools, json, subprocess, sys, time
import numpy as np
t00 = time.time()
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1:
            M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
Uop = lambda i, j: c[i] @ cd[2 + j]
res = lambda M: M[np.ix_(SECTOR, SECTOR)]
Ub = [[res(Uop(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Ub[i][j].T for j in range(2)] for i in range(2)]
dU = res(Uop(0, 0) @ Uop(1, 1) - Uop(0, 1) @ Uop(1, 0)); hd = dU + dU.T
def kron4(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]]) for a, b, cc, d in itertools.product(range(2), repeat=4))
HB = -(W + W.T)
HD = sum(kron4([hd if l == k else np.eye(6) for l in range(4)]) for k in range(4))
cas = np.array([0, .75, .75, .75, .75, 0.])
HE = np.array([sum(cas[(i // 6 ** l) % 6] for l in range(4)) for i in range(1296)])
wB, VB = np.linalg.eigh(HB); wD, VD = np.linalg.eigh(HD)
UBf = lambda b: (VB * np.exp(-1j * b * wB)) @ VB.T
UDf = lambda e: (VD * np.exp(-1j * e * wD)) @ VD.T
UEf = lambda a: np.diag(np.exp(-1j * a * HE))
def own_U1(a, b, e): return UBf(b) @ UDf(e) @ UEf(a)
def own_U2(a, b, e): return (UEf(a / 2) @ UDf(e / 2)) @ UBf(b) @ (UDf(e / 2) @ UEf(a / 2))
codes = np.array([sum(SECTOR[(i // 6 ** l) % 6] << (4 * l) for l in range(4)) for i in range(1296)], dtype=np.int64)
cidx = {int(cc): i for i, cc in enumerate(codes)}

# ---------------- own sparse simulator ----------------
def merge(idx, amp, drop):
    o = np.argsort(idx, kind="stable"); idx = idx[o]; amp = amp[o]
    first = np.concatenate(([True], idx[1:] != idx[:-1]))
    st = np.flatnonzero(first)
    a = np.add.reduceat(amp, st); ii = idx[st]
    keep = np.abs(a) > 1e-15
    drop[0] += float((np.abs(a[~keep]) ** 2).sum())
    return ii[keep], a[keep]
def run(qc, start_code, drop):
    idx = np.array([start_code], dtype=np.int64); amp = np.array([1.0 + 0j]); n = 0
    for ins in qc.data:
        nm = ins.operation.name
        if nm == "barrier": continue
        q = [qc.find_bit(x).index for x in ins.qubits]; p = [float(x) for x in ins.operation.params]
        bit = lambda k: (idx >> k) & 1
        if nm == "x": idx = idx ^ (1 << q[0])
        elif nm == "cx": idx = np.where(bit(q[0]) == 1, idx ^ (1 << q[1]), idx)
        elif nm == "ccx": idx = np.where((bit(q[0]) & bit(q[1])) == 1, idx ^ (1 << q[2]), idx)
        elif nm == "z": amp = amp * (1 - 2 * bit(q[0]))
        elif nm == "cz": amp = amp * (1 - 2 * (bit(q[0]) & bit(q[1])))
        elif nm == "p": amp = amp * np.where(bit(q[0]) == 1, np.exp(1j * p[0]), 1.0)
        elif nm == "rz": amp = amp * np.where(bit(q[0]) == 1, np.exp(1j * p[0] / 2), np.exp(-1j * p[0] / 2))
        elif nm in ("h", "ch", "crx"):
            ctrl = (np.ones(len(idx), bool) if nm == "h" else bit(q[0]) == 1); t = q[-1]
            if nm == "crx": M = np.array([[np.cos(p[0] / 2), -1j * np.sin(p[0] / 2)], [-1j * np.sin(p[0] / 2), np.cos(p[0] / 2)]])
            else: M = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
            tb = bit(t); i0 = idx & ~(np.int64(1) << t); i1 = i0 | (np.int64(1) << t)
            a0 = np.where(tb == 0, amp, 0); a1 = np.where(tb == 1, amp, 0)       # amplitude components on target 0/1 (only one non-zero per entry)
            n0 = M[0, 0] * a0 + M[0, 1] * a1; n1 = M[1, 0] * a0 + M[1, 1] * a1
            idx = np.concatenate((np.where(ctrl, i0, idx), np.where(ctrl, i1, idx)[ctrl]))
            amp = np.concatenate((np.where(ctrl, n0, amp), n1[ctrl]))
            idx, amp = merge(idx, amp, drop)
        else:
            raise ValueError("gate not supported by my simulator: " + nm)
        n = max(n, len(idx))
    return idx, amp, n
def column(qc, code):
    drop = [0.0]
    idx, amp, nmax = run(qc, int(code), drop)
    inner_mask = idx >> 16 == 0                          # ancillas (bits 16..25) must be 0
    leak = float(np.linalg.norm(amp[~inner_mask]))
    col = np.zeros(1296, complex); lost = 0.0
    for i, a in zip(idx[inner_mask], amp[inner_mask]):
        j = cidx.get(int(i))
        if j is None: lost += abs(a) ** 2
        else: col[j] = a
    return col, leak, float(np.sqrt(lost)), float(np.sqrt(drop[0])), nmax

sys.path.insert(0, "src")
from su2plaq.circuits import rishon as R
rng = np.random.default_rng(20261110)
# vac_A code: link order b, r, t, l = A, A, B, B (sector index 0,0,5,5 -> codes 3,3,12,12) as in the plan; read from production for the comparison only
from su2plaq.rishon import operators as ops
va, _, _ = ops.closed_codes()
i_vac = cidx[int(va)]
inputs = [i_vac] + [int(x) for x in rng.choice(1296, 40, replace=False)]
rec = {"inputs": inputs, "vacA_inner_index": i_vac, "cases": []}
TRIPLES = ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))
def check(a, b, e, order, mutate=None):
    qc = R.build_step(a, b, order, eta=e)
    own = (own_U1 if order == 1 else own_U2)(a, b, e)
    maxerr = 0.0; maxleak = 0.0; maxlost = 0.0; maxdrop = 0.0; nmax = 0; phs = []
    cols = []
    for i in inputs:
        col, leak, lost, dr, nm = column(qc, codes[i]); cols.append(col)
        maxleak = max(maxleak, leak); maxlost = max(maxlost, lost); maxdrop = max(maxdrop, dr); nmax = max(nmax, nm)
    C = np.array(cols).T; T = own[:, inputs]
    ph = np.vdot(T, C); ph /= abs(ph)
    err = float(np.abs(C - ph * T).max()); err2 = float(np.max(np.linalg.norm(C - ph * T, axis=0)))
    return {"alpha": a, "beta": b, "eta": e, "order": order, "max_abs_err_vs_own": err, "max_col_l2_err_vs_own": err2, "global_phase": complex(ph),
            "max_leak_l2": maxleak, "max_invalid_code_l2": maxlost, "max_dropped_l2": maxdrop, "max_support": nmax, "n_inputs": len(inputs), "cols": C}
t = time.time()
for (a, b, e) in TRIPLES:
    for order in (1, 2):
        r = check(a, b, e, order)
        # wrong-order discrimination: own U_E U_D U_B (det layer after U_B) against the same circuit columns
        T_wrong = (UEf(a) @ UDf(e) @ UBf(b))[:, inputs]; C = r.pop("cols")
        if order == 1:
            ph = np.vdot(T_wrong, C); ph /= abs(ph); r["wrong_order_distance_l2"] = float(np.max(np.linalg.norm(C - ph * T_wrong, axis=0)))
        T_nodet = (own_U1 if order == 1 else own_U2)(a, b, 0.0)[:, inputs]; ph = np.vdot(T_nodet, C); ph /= abs(ph)
        r["no_det_distance_l2"] = float(np.max(np.linalg.norm(C - ph * T_nodet, axis=0)))
        r["t_s"] = time.time() - t; t = time.time()
        rec["cases"].append(r); print({k: v for k, v in r.items()}, flush=True)
# eta=None circuits against own two-layer
for order in (1, 2):
    qc = R.build_step(0.37, 0.61, order)
    T = (own_U1 if order == 1 else own_U2)(0.37, 0.61, 0.0)[:, inputs]
    C = np.array([column(qc, codes[i])[0] for i in inputs]).T; ph = np.vdot(T, C); ph /= abs(ph)
    rec[f"eta_none_order{order}_max_abs_err"] = float(np.abs(C - ph * T).max())
# Trotter slopes from circuit columns: distance to exact exp(-i dt H) on the same inputs (column-wise 2-norm max), g2 = 1.1014, lam_D = 0.4316
g2, lam = 1.1014, 0.4316
Hfull = g2 / 2 * np.diag(HE) + HB / g2 + lam * HD
wH, VH = np.linalg.eigh(Hfull)
sl = {}
for order in (1, 2):
    errs = []
    for dt in (0.1, 0.05, 0.025, 0.0125):
        a, b, e = g2 * dt / 2, dt / g2, lam * dt
        qc = R.build_step(a, b, order, eta=e)
        C = np.array([column(qc, codes[i])[0] for i in inputs]).T
        ex = ((VH * np.exp(-1j * dt * wH)) @ VH.conj().T)[:, inputs]
        ph = np.vdot(ex, C); ph /= abs(ph)
        errs.append(float(np.max(np.linalg.norm(C - ph * ex, axis=0))))
    s = [float(np.log(errs[i] / errs[i + 1]) / np.log(2)) for i in range(3)]
    sl[str(order)] = {"dt": [0.1, 0.05, 0.025, 0.0125], "err_colmax": errs, "slopes": s}
    print("order", order, errs, s, flush=True)
rec["trotter_slopes_from_circuits"] = sl
rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(); rec["t_total_s"] = time.time() - t00
json.dump(rec, open("results/rishon/tester-223-step-orders.json", "w"), indent=1, default=str)
print("done", rec["t_total_s"])
