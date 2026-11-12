"""Tester 223 (rishon D3): the det-layer circuits against my own det-term target, on all 1296 physical inner codes, three eta.
Own pieces: JW link algebra (as tester-222-det-independent.py), H_D^in = sum_l (det U_l + h.c.), U_D = expm(-i eta H_D^in) by eigh
(cross-checked with scipy expm), and my own numpy gate applier (h, cx, rz, taken from qc.data; qiskit Operator is not used).
Production is used only to build the circuits (build_UD, prepend_det_layer on a trivial unit).  Run: PYTHONPATH=src python this.
Output: results/rishon/tester-223-det-circuits.json"""
import itertools, json, subprocess, time
import numpy as np
from scipy.linalg import expm
t00 = time.time()
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1:
            M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
U = lambda i, j: c[i] @ cd[2 + j]
detU = U(0, 0) @ U(1, 1) - U(0, 1) @ U(1, 0)
HDl = detU + detU.T                                            # 16 x 16 per link, my own
sec_pos = {s: i for i, s in enumerate(SECTOR)}
def kron_all(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
# H_D on the 4-link inner space (16 qubits, 65536 dim, little-endian) is a sum of link terms; U_D = tensor product of per-link expm(-i eta HDl)
# (the terms commute: disjoint links), which I use as the target on the full 65536-dim space (no restriction to valid codes).
def ud_target_full(eta):                                       # as a function applying to a batch of states, see apply_target
    return expm(-1j * eta * HDl)
def apply_link_ops(psi, M, links):
    """psi: (B, 2^16) little-endian; apply 16x16 M to the nibble of every link in `links` (nibble l = bits 4l..4l+3)."""
    B = psi.shape[0]
    for l in links:
        v = psi.reshape(B, 2 ** (12 - 4 * l), 16, 2 ** (4 * l))   # index = hi * 16 * 2^(4l) + nib * 2^(4l) + lo
        psi = np.einsum("ab,xybz->xyaz", M, v.reshape(B, -1, 16, 2 ** (4 * l))).reshape(B, -1) if False else np.einsum("ab,pxbz->pxaz", M, v).reshape(B, -1)
    return psi
# ---- own gate applier for h, cx, rz on a batch of 16-qubit states -------------------------------------------------
def apply_gate(psi, name, qs, params, n):
    B = psi.shape[0]
    v = psi.reshape((B,) + (2,) * n)                          # axis 1 + (n-1-q) = qubit q
    ax = lambda q: 1 + (n - 1 - q)
    if name == "h":
        a = ax(qs[0]); v0 = np.take(v, 0, axis=a).copy(); v1 = np.take(v, 1, axis=a).copy()
        s = 1 / np.sqrt(2)
        out = np.empty_like(v)
        sl0 = [slice(None)] * (n + 1); sl0[a] = 0; sl1 = [slice(None)] * (n + 1); sl1[a] = 1
        out[tuple(sl0)] = s * (v0 + v1); out[tuple(sl1)] = s * (v0 - v1)
        return out.reshape(B, -1)
    if name == "rz":                                          # qiskit rz(theta) = exp(-i theta Z/2)
        th = params[0]; a = ax(qs[0]); out = v.copy()
        sl0 = [slice(None)] * (n + 1); sl0[a] = 0; sl1 = [slice(None)] * (n + 1); sl1[a] = 1
        out[tuple(sl0)] *= np.exp(-1j * th / 2); out[tuple(sl1)] *= np.exp(1j * th / 2)
        return out.reshape(B, -1)
    if name == "cx":
        ac, at = ax(qs[0]), ax(qs[1]); out = v.copy()
        sl = [slice(None)] * (n + 1); sl[ac] = 1
        sub = out[tuple(sl)]                                  # view with control = 1; target axis shifts by -1 if at > ac
        at2 = at - 1 if at > ac else at
        sub[:] = np.flip(sub, axis=at2)
        return out.reshape(B, -1)
    raise ValueError(name)
def simulate(qc, psi):
    n = qc.num_qubits
    for ins in qc.data:
        nm = ins.operation.name
        if nm == "barrier": continue
        qs = [qc.find_bit(q).index for q in ins.qubits]
        psi = apply_gate(psi, nm, qs, [float(p) for p in ins.operation.params], n)
    return psi
# self-test of the applier on a random 3-qubit circuit vs dense matrices
rng = np.random.default_rng(20261110)
def dense_h(q, n): 
    M = np.array([[1, 1], [1, -1]]) / np.sqrt(2); return np.kron(np.kron(np.eye(2 ** (n - 1 - q)), M), np.eye(2 ** q))
def dense_cx(c_, t_, n):
    D = 2 ** n; M = np.zeros((D, D))
    for i in range(D): M[i ^ (1 << t_) if (i >> c_) & 1 else i, i] = 1
    return M
def dense_rz(th, q, n):
    return np.kron(np.kron(np.eye(2 ** (n - 1 - q)), np.diag([np.exp(-1j * th / 2), np.exp(1j * th / 2)])), np.eye(2 ** q))
n = 4; x = rng.normal(size=(3, 2 ** n)) + 1j * rng.normal(size=(3, 2 ** n)); y = x.copy(); Dm = np.eye(2 ** n, dtype=complex)
for g in [("h", (1,), ()), ("cx", (0, 3), ()), ("rz", (2,), (0.7,)), ("cx", (3, 1), ()), ("h", (3,), ()), ("cx", (2, 0), ())]:
    y = apply_gate(y, g[0], g[1], g[2], n)
    Mg = {"h": lambda: dense_h(g[1][0], n), "cx": lambda: dense_cx(g[1][0], g[1][1], n), "rz": lambda: dense_rz(g[2][0], g[1][0], n)}[g[0]]()
    x = (Mg @ x.T).T
applier_selftest = float(np.abs(x - y).max())

# ---- inputs: all 1296 valid inner codes, in chunks ----
codes = np.array([sum(SECTOR[(i // 6 ** l) % 6] << (4 * l) for l in range(4)) for i in range(1296)], dtype=np.int64)
valid = np.zeros(65536, bool); valid[codes] = True
import sys; sys.path.insert(0, "src")
from su2plaq.circuits import rishon as R
rec = {"applier_selftest": applier_selftest, "etas": {}}
wD, VD = None, None
# own U_D on the 1296 space for the cross-check of the closed form (eigh of own H_D^in)
def own_UD_columns(eta, idx):                                  # columns idx of the full 65536 target: tensor product of link expm on basis codes
    E = expm(-1j * eta * HDl)
    out = np.zeros((len(idx), 65536), complex)
    for r, i in enumerate(idx):
        # product state of links; link l is in code nibble(i, l); amplitude vector over each link's 16 states
        vec = np.ones(1, complex)
        for l in range(4):
            nib = (int(codes[i]) >> (4 * l)) & 15
            vec = np.kron(E[:, nib], vec)                     # link 0 least significant
        out[r] = vec
    return out
# eigh-based check of the closed form target against the 1296-dim own H_D^in (once)
Ub = [[U(i, j)[np.ix_(SECTOR, SECTOR)] for j in range(2)] for i in range(2)]
HDin = sum(kron_all([(detU[np.ix_(SECTOR, SECTOR)] + detU[np.ix_(SECTOR, SECTOR)].T) if l == k else np.eye(6) for l in range(4)]) for k in range(4))
w, V = np.linalg.eigh(HDin)
rec["own_HDin_spectrum_ok"] = {str(k): int(v) for k, v in zip(*np.unique(np.round(w, 6), return_counts=True))}
for eta in (0.29, 0.53, 1.07):
    t = time.time()
    qc = R.build_UD(eta)
    ops = dict(qc.count_ops())
    gate_names_ok = set(ops) <= {"h", "cx", "rz"}
    rz_angles = sorted({round(float(i.operation.params[0]), 14) for i in qc.data if i.operation.name == "rz"})
    max_err_valid = 0.0; max_leak = 0.0; ph_all = []; maxdev_eigh = 0.0
    E1296 = (V * np.exp(-1j * eta * w)) @ V.conj().T
    for chunk in np.array_split(np.arange(1296), 6):
        psi = np.zeros((len(chunk), 65536), complex); psi[np.arange(len(chunk)), codes[chunk]] = 1
        out = simulate(qc, psi)
        tgt = own_UD_columns(eta, chunk)
        ph = np.vdot(tgt, out); ph /= abs(ph); ph_all.append(ph)
        max_err_valid = max(max_err_valid, float(np.abs(out - ph * tgt).max()))
        max_leak = max(max_leak, float(np.abs(out[:, ~valid]).max()))
        # restriction of the closed-form target to the valid codes == eigh target (own cross-check, once per chunk)
        maxdev_eigh = max(maxdev_eigh, float(np.abs(tgt[:, codes] - E1296[:, chunk].T).max()))
    # wrong-sign / wrong-angle discrimination on one chunk: compare with exp(+i eta H)
    chunk = np.arange(0, 1296, 37)
    psi = np.zeros((len(chunk), 65536), complex); psi[np.arange(len(chunk)), codes[chunk]] = 1
    out = simulate(qc, psi)
    wrong = own_UD_columns(-eta, chunk); phw = np.vdot(wrong, out); phw /= abs(phw)
    sep_sign = float(np.abs(out - phw * wrong).max())
    rec["etas"][str(eta)] = {"count_ops": {k: int(v) for k, v in ops.items()}, "gate_names_subset_of_h_cx_rz": bool(gate_names_ok),
        "rz_angles": rz_angles, "two_eta": 2 * eta, "n_qubits": qc.num_qubits, "global_phase_attr": float(qc.global_phase),
        "max_amp_error_vs_own_target_on_1296_codes": max_err_valid, "global_phase_fitted": [complex(p) for p in ph_all[:1]], "max_phase_spread": float(max(abs(p - ph_all[0]) for p in ph_all)),
        "max_amplitude_on_invalid_codes": max_leak, "closed_form_vs_eigh_valid_block": maxdev_eigh,
        "sign_flipped_target_distance": sep_sign, "t_s": time.time() - t}
    print(eta, rec["etas"][str(eta)])
# prepend_det_layer on a trivial unit: [det gadgets then unit] == build_UD followed by the unit's gates; qubit registers
from qiskit import QuantumCircuit, QuantumRegister
d = QuantumRegister(16, "d"); unit = QuantumCircuit(d); unit.h(3); unit.cx(3, 7); unit.rz(0.4, 7)
full = R.prepend_det_layer(unit, 0.29)
ref = R.build_UD(0.29); ref2 = QuantumCircuit(d)
for ins in ref.data: ref2.append(ins.operation, [d[ref.find_bit(q).index] for q in ins.qubits])
for ins in unit.data: ref2.append(ins.operation, list(ins.qubits))
rec["prepend_equals_UD_then_unit"] = [(a.operation.name, [full.find_bit(q).index for q in a.qubits], list(map(float, a.operation.params))) for a in full.data] == \
    [(a.operation.name, [ref2.find_bit(q).index for q in a.qubits], list(map(float, a.operation.params))) for a in ref2.data]
rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(); rec["t_total_s"] = time.time() - t00
json.dump(rec, open("results/rishon/tester-223-det-circuits.json", "w"), indent=1, default=str)
print("done", rec["t_total_s"], rec["prepend_equals_UD_then_unit"])
