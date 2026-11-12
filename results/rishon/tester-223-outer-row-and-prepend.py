"""Tester 223 (rishon D3/D5): (1) the 12-link det row on 48 qubits against my own tensor product of per-link targets (own sparse simulator,
24 seeded random products of sector codes, three eta), (2) results.outer_det_certify bounds and gate counts, (3) prepend_det_layer(two-layer
unit, eta) equals the three-layer step U_B U_D U_E (own composition) on 41 inputs, and rejects a unit whose first register is not d[16],
(4) build_step(eta=None) is gate-for-gate identical to HEAD (module loaded from `git show HEAD:...`).  Run: PYTHONPATH=src python this.
Output: results/rishon/tester-223-outer-row-and-prepend.json"""
import importlib.util, itertools, json, subprocess, sys, time, types
import numpy as np
t00 = time.time()
sys.path.insert(0, "src")
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1: M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
Uop = lambda i, j: c[i] @ cd[2 + j]
detU = Uop(0, 0) @ Uop(1, 1) - Uop(0, 1) @ Uop(1, 0); HDl = detU + detU.T
from scipy.linalg import expm
# ---- sparse simulator (same as tester-223-step-orders.py, generalised to 48-bit indices) ----
def merge(idx, amp):
    o = np.argsort(idx, kind="stable"); idx = idx[o]; amp = amp[o]
    first = np.concatenate(([True], idx[1:] != idx[:-1])); st = np.flatnonzero(first)
    a = np.add.reduceat(amp, st); ii = idx[st]; keep = np.abs(a) > 1e-15
    return ii[keep], a[keep]
def run(qc, start):
    idx = np.array([start], dtype=np.int64); amp = np.array([1.0 + 0j])
    for ins in qc.data:
        nm = ins.operation.name
        if nm == "barrier": continue
        q = [qc.find_bit(x).index for x in ins.qubits]; p = [float(x) for x in ins.operation.params]
        bit = lambda k: (idx >> k) & 1
        if nm == "x": idx = idx ^ (1 << q[0])
        elif nm == "cx": idx = np.where(bit(q[0]) == 1, idx ^ (1 << q[1]), idx)
        elif nm == "rz": amp = amp * np.where(bit(q[0]) == 1, np.exp(1j * p[0] / 2), np.exp(-1j * p[0] / 2))
        elif nm == "h":
            t = q[0]; tb = bit(t); i0 = idx & ~(np.int64(1) << t); i1 = i0 | (np.int64(1) << t)
            a0 = np.where(tb == 0, amp, 0); a1 = np.where(tb == 1, amp, 0); s = 1 / np.sqrt(2)
            idx = np.concatenate((i0, i1)); amp = np.concatenate((s * (a0 + a1), s * (a0 - a1))); idx, amp = merge(idx, amp)
        else: raise ValueError(nm)
    return idx, amp
from su2plaq.circuits import rishon as R
rec = {"outer_row": {}}
rng = np.random.default_rng(20261110)
for eta in (0.29, 0.53, 1.07):
    qc = R.build_UD(eta, with_outer=True, include_outer_det=True)
    ops = {k: int(v) for k, v in qc.count_ops().items()}
    E = expm(-1j * eta * HDl)
    errs = []; leak = 0.0; nlinks_touched = sorted({qc.find_bit(q).index // 4 for ins in qc.data for q in ins.qubits}); crosslink = 0
    for ins in qc.data:
        if len({qc.find_bit(q).index // 4 for q in ins.qubits}) != 1: crosslink += 1
    phs = []
    for trial in range(24):
        sec = rng.integers(0, 6, size=12); code = sum(SECTOR[s] << (4 * l) for l, s in enumerate(sec))
        idx, amp = run(qc, int(code))
        # own tensor product target: link l in code nib_l -> column nib_l of expm(-i eta HDl)
        vec_idx = np.zeros(1, dtype=np.int64); vec_amp = np.ones(1, complex)
        for l in range(12):
            col = E[:, SECTOR[sec[l]]]; nzs = np.flatnonzero(np.abs(col) > 1e-15)
            vec_idx = (vec_idx[:, None] | (nzs[None, :].astype(np.int64) << (4 * l))).ravel(); vec_amp = (vec_amp[:, None] * col[nzs][None, :]).ravel()
        o = np.argsort(vec_idx); vec_idx, vec_amp = vec_idx[o], vec_amp[o]
        # compare as dense dictionaries
        d1 = dict(zip(idx.tolist(), amp)); d2 = dict(zip(vec_idx.tolist(), vec_amp))
        keys = set(d1) | set(d2)
        ph = sum(np.conj(d2.get(k, 0)) * d1.get(k, 0) for k in keys); ph /= abs(ph); phs.append(complex(ph))
        errs.append(max(abs(d1.get(k, 0) - ph * d2.get(k, 0)) for k in keys))
    res = __import__("su2plaq.rishon.results", fromlist=["x"]).outer_det_certify(qc, __import__("su2plaq.encodings.rishon", fromlist=["x"]).RishonEncoding(), eta)
    rec["outer_row"][str(eta)] = {"count_ops": ops, "n_qubits": qc.num_qubits, "links_touched": nlinks_touched, "cross_link_gates": crosslink,
        "max_amp_err_vs_own_product_target_24_inputs": float(max(errs)), "phase_fitted_first": phs[0],
        "outer_det_certify": {k: (v if not isinstance(v, (list, complex)) else (list(map(float, v)) if isinstance(v, list) and v and not isinstance(v[0], int) else str(v)))
                              for k, v in res.items() if k in ("certified", "ok", "reason", "error_bound", "max_link_error", "n_links", "method", "gates_per_link", "link_errors")}}
    print(eta, rec["outer_row"][str(eta)]["max_amp_err_vs_own_product_target_24_inputs"], res["error_bound"], res["certified"], ops, flush=True)
# ---- prepend_det_layer ----
from su2plaq.rishon import operators as ops_
codes = np.array(sorted(sum(SECTOR[s] << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(range(6), repeat=4)), dtype=np.int64)
# own 1296-dim operators (from the same JW algebra)
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
cidx = {int(cc): i for i, cc in enumerate(codes)}
# extend simulator for the unit's gates (ccx, ch, crx, cz, z, p)
def run2(qc, start):
    idx = np.array([start], dtype=np.int64); amp = np.array([1.0 + 0j])
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
            M = (np.array([[np.cos(p[0] / 2), -1j * np.sin(p[0] / 2)], [-1j * np.sin(p[0] / 2), np.cos(p[0] / 2)]]) if nm == "crx" else np.array([[1, 1], [1, -1]]) / np.sqrt(2))
            tb = bit(t); i0 = idx & ~(np.int64(1) << t); i1 = i0 | (np.int64(1) << t)
            a0 = np.where(tb == 0, amp, 0); a1 = np.where(tb == 1, amp, 0)
            n0 = M[0, 0] * a0 + M[0, 1] * a1; n1 = M[1, 0] * a0 + M[1, 1] * a1
            idx = np.concatenate((np.where(ctrl, i0, idx), np.where(ctrl, i1, idx)[ctrl])); amp = np.concatenate((np.where(ctrl, n0, amp), n1[ctrl])); idx, amp = merge(idx, amp)
        else: raise ValueError(nm)
    return idx, amp
def col(qc, code):
    idx, amp = run2(qc, int(code)); out = np.zeros(1296, complex); leak = 0.0
    for i, a in zip(idx, amp):
        if (int(i) >> 16) != 0 or int(i) not in cidx: leak += abs(a) ** 2
        else: out[cidx[int(i)]] = a
    return out, np.sqrt(leak)
rng2 = np.random.default_rng(20261110)
inputs = [int(x) for x in rng2.choice(1296, 41, replace=False)]
rec["prepend"] = []
for (a, b, e) in ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07)):
    unit = R.build_step(a, b, 1)
    full = R.prepend_det_layer(unit, e)
    T = (UBf(b) @ UDf(e) @ UEf(a))[:, inputs]; Tw = (UDf(e) @ UBf(b) @ UEf(a))[:, inputs]
    C = []; lk = 0.0
    for i in inputs:
        cc_, l = col(full, codes[i]); C.append(cc_); lk = max(lk, l)
    C = np.array(C).T; ph = np.vdot(T, C); ph /= abs(ph); phw = np.vdot(Tw, C); phw /= abs(phw)
    ops_u, ops_f = dict(unit.count_ops()), dict(full.count_ops())
    rec["prepend"].append({"triple": [a, b, e], "max_abs_err_vs_own_UB_UD_UE": float(np.abs(C - ph * T).max()), "distance_to_wrong_order_UD_UB_UE": float(np.max(np.linalg.norm(C - phw * Tw, axis=0))),
                           "max_leak": lk, "cx_unit": ops_u.get("cx"), "cx_full": ops_f.get("cx"), "rz_added": ops_f.get("rz", 0) - ops_u.get("rz", 0), "h_added": ops_f.get("h", 0) - ops_u.get("h", 0),
                           "unit_instructions_preserved_in_order": [x.operation.name for x in full.data][-len(unit.data):] == [x.operation.name for x in unit.data],
                           "qregs": [(r.name, r.size) for r in full.qregs], "metadata": full.metadata}); print(rec["prepend"][-1], flush=True)
# first-register check
from qiskit import QuantumCircuit, QuantumRegister
bad = QuantumCircuit(QuantumRegister(15, "d")); bad2 = QuantumCircuit(QuantumRegister(16, "x")); ok1 = ok2 = False
for q_, nm in ((bad, "d15"), (bad2, "x16")):
    try: R.prepend_det_layer(q_, 0.3)
    except ValueError: rec.setdefault("prepend_value_error", []).append(nm)
# ---- eta=None vs HEAD ----
src = subprocess.check_output(["git", "show", "HEAD:src/su2plaq/circuits/rishon.py"], text=True)
mod = types.ModuleType("rishon_head"); mod.__package__ = "su2plaq.circuits"; mod.__file__ = "rishon_head.py"
exec(compile(src, "rishon_head.py", "exec"), mod.__dict__)
def sig(q): return [(i.operation.name, tuple(q.find_bit(x).index for x in i.qubits), tuple(float(p) for p in i.operation.params)) for i in q.data]
same = []
for (a, b) in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.0), (0.0, 0.5)):
    for order in (1, 2):
        for ladder in ("ccx", "rccx", "mcx"):
            for wo in (False, True):
                try: old = mod.build_step(a, b, order, wo, ladder)
                except Exception as ex: same.append(("old_failed", str(ex)[:40])); continue
                new = R.build_step(a, b, order, wo, ladder); new2 = R.build_step(a, b, order, wo, ladder, eta=None)
                same.append(sig(old) == sig(new) == sig(new2) and old.global_phase == new.global_phase and old.metadata == new.metadata == new2.metadata
                            and [(r.name, r.size) for r in old.qregs] == [(r.name, r.size) for r in new.qregs])
rec["eta_none_vs_HEAD"] = {"n_circuits": len(same), "all_identical": all(x is True for x in same), "detail_non_true": [x for x in same if x is not True]}
for nm in ("build_UE", "build_UB"):
    pass
for (a,) in ((0.37,), (1.1,)):
    rec["eta_none_vs_HEAD"][f"UE({a})"] = sig(mod.build_UE(a)) == sig(R.build_UE(a))
for (b,) in ((0.61,), (1.0,)):
    for lad in ("ccx", "rccx"):
        rec["eta_none_vs_HEAD"][f"UB({b},{lad})"] = sig(mod.build_UB(b, ladder=lad)) == sig(R.build_UB(b, ladder=lad))
print(rec["eta_none_vs_HEAD"], rec.get("prepend_value_error"))
rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(); rec["t_total_s"] = time.time() - t00
json.dump(rec, open("results/rishon/tester-223-outer-row-and-prepend.json", "w"), indent=1, default=str)
print("done", rec["t_total_s"])
