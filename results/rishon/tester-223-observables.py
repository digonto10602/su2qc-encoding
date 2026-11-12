"""Tester 223 (rishon D4): observables(eta=) and closed_spectra(lam_d) against my own 1296-dim composition (JW algebra as before).
E_link = <H_E>/4, P = -<H_B>/2, echo = |<vac_A|U^n|vac_A>|^2, n = 1, 2, first-order three-layer step U_B U_D U_E from vac_A; closed spectra of
H(g2, lam_d) restricted to the closed 17-state sector from my own 1296 H (invariant subspace spanned by 16 vacua {A,B}^4 + loop).
Production (observables, closed_spectra, det_observables_table) imported after my numbers exist.  Run: PYTHONPATH=src python this."""
import itertools, json, subprocess, sys
import numpy as np
sys.path.insert(0, "src")
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1: M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
Uop = lambda i, j: c[i] @ cd[2 + j]; res = lambda M: M[np.ix_(SECTOR, SECTOR)]
Ub = [[res(Uop(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Ub[i][j].T for j in range(2)] for i in range(2)]
dU = res(Uop(0, 0) @ Uop(1, 1) - Uop(0, 1) @ Uop(1, 0)); hd = dU + dU.T
def kron4(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]]) for a, b, cc, d in itertools.product(range(2), repeat=4)); HB = -(W + W.T)
HD = sum(kron4([hd if l == k else np.eye(6) for l in range(4)]) for k in range(4))
cas = np.array([0, .75, .75, .75, .75, 0.]); HE = np.array([sum(cas[(i // 6 ** l) % 6] for l in range(4)) for i in range(1296)])
wB, VB = np.linalg.eigh(HB); wD, VD = np.linalg.eigh(HD)
UBf = lambda b: (VB * np.exp(-1j * b * wB)) @ VB.T; UDf = lambda e: (VD * np.exp(-1j * e * wD)) @ VD.T; UEf = lambda a: np.diag(np.exp(-1j * a * HE))
from su2plaq.rishon import operators as ops, observables as Ob
va, _, _ = ops.closed_codes()
codes = np.array(sorted(sum(SECTOR[(i // 6 ** l) % 6] << (4 * l) for l in range(4)) for i in range(1296)))
i0 = int(np.flatnonzero(codes == int(va))[0]); psi0 = np.zeros(1296, complex); psi0[i0] = 1
rec = {"observables": [], "closed_spectra": []}
maxdev = 0.0
for (a, b, e) in ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07)):
    U = UBf(b) @ UDf(e) @ UEf(a); psi = psi0.copy(); prod = Ob.observables(a, b, n_steps=2, eta=e)["rishon"]
    base = Ob.observables(a, b, n_steps=2)["rishon"]
    for n in (1, 2):
        psi = U @ psi
        own = {"E_link": float(0.25 * np.real(np.vdot(psi, HE * psi))), "P": float(-0.5 * np.real(np.vdot(psi, HB @ psi))), "echo": float(abs(np.vdot(psi0, psi)) ** 2)}
        dev = {k: abs(own[k] - prod[n][k]) for k in own}; maxdev = max(maxdev, *dev.values())
        rec["observables"].append({"triple": [a, b, e], "n": n, "own": own, "production": {k: prod[n][k] for k in own}, "dev": dev,
                                   "no_det_production": {k: base[n][k] for k in own}, "norm": float(np.linalg.norm(psi))})
rec["max_dev_observables"] = maxdev
# closed spectra: own 17-dim block
idx = lambda bits: sum((5 if bits[l] else 0) * 6 ** l for l in range(4))
vacs = np.zeros((1296, 17))
for n, bits in enumerate(itertools.product((0, 1), repeat=4)): vacs[idx(bits), n] = 1
loop = -(HB @ psi0.real) / 4.0; loop /= np.linalg.norm(loop); vacs[:, 16] = loop
mdev = 0.0
for g2 in (0.5, 1.0, 2.0):
    for lam in (0.0, 0.2, 0.5):
        H = g2 / 2 * np.diag(HE) + HB / g2 + lam * HD
        inv = float(np.abs(H @ vacs - vacs @ (vacs.T @ H @ vacs)).max())
        ev = np.sort(np.linalg.eigvalsh(vacs.T @ H @ vacs))
        sp = Ob.closed_spectra((g2,), lam_d=lam)["rishon"][g2]
        full = np.sort(np.repeat(np.array(sp["eigenvalues"]), np.array(sp["multiplicities"])))
        d = float(np.abs(full - ev).max()) if len(full) == 17 else 9.0; mdev = max(mdev, d)
        rec["closed_spectra"].append({"g2": g2, "lam_d": lam, "invariance_defect": inv, "dev_eigs": d, "n_zero_levels": int(np.sum(np.abs(ev) < 1e-9)), "mult": sp["multiplicities"]})
rec["max_dev_closed_spectra"] = mdev
# lam_d = 0 unchanged; eta = None / 0.0
a, b, e = 0.37, 0.61, 0.29
base = Ob.observables(a, b, n_steps=2); none = Ob.observables(a, b, n_steps=2, eta=None); zero = Ob.observables(a, b, n_steps=2, eta=0.0)
rec["eta_none_identical"] = base == none; rec["eta_zero_max_dev"] = max(abs(zero["rishon"][n][k] - base["rishon"][n][k]) for n in (1, 2) for k in ("E_link", "P", "echo"))
rec["ks_unchanged_with_eta"] = Ob.observables(a, b, n_steps=2, eta=e)["ks"] == base["ks"]
cs0 = Ob.closed_spectra((0.5, 1.0, 2.0)); cs0b = Ob.closed_spectra((0.5, 1.0, 2.0), lam_d=0.0)
rec["closed_spectra_lam0_identical"] = cs0 == cs0b
# production table vs quick output of the script (if present) is checked elsewhere; here: table schema
t = Ob.det_observables_table(triples=((0.37, 0.61, 0.29),), lam_d_list=(0.0, 0.2), g2_list=(1.0,))
rec["table_keys"] = sorted(t.keys())
rec["P1_zero"] = max(abs(r["1"]["P"]) for r in t["rishon"])
rec["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
json.dump(rec, open("results/rishon/tester-223-observables.json", "w"), indent=1, default=str)
print({k: rec[k] for k in ("max_dev_observables", "max_dev_closed_spectra", "eta_none_identical", "eta_zero_max_dev", "ks_unchanged_with_eta", "closed_spectra_lam0_identical", "P1_zero", "table_keys")})
print([ (r["g2"], r["lam_d"], r["n_zero_levels"], r["invariance_defect"]) for r in rec["closed_spectra"]])
