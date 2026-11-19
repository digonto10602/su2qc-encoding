"""Tester 434 item 2: exact Laurent targets (lean_cert.exact_target) vs an independent dense-expm float construction at random angles.
Independent = H_E, H_B (W), H_D rebuilt here from RishonLink with my own kron code; U = scipy.linalg.expm; no bright pairs."""
import itertools, json, hashlib, subprocess, sys
import numpy as np, scipy.linalg as sla
from su2plaq.rishon.algebra import RishonLink
from su2plaq.rishon import lean_cert as LC

rl = RishonLink()
sec = [int(s) for s in rl.sector]
assert sec == [3, 5, 6, 9, 10, 12], sec
def R(M): return np.asarray(M)[np.ix_(sec, sec)].astype(complex)
U = [[R(rl.U(i, j)) for j in range(2)] for i in range(2)]
Ud = [[R(rl.Udag(i, j)) for j in range(2)] for i in range(2)]
def kron4(ms):           # ms[l]; link 0 least significant -> kron(m3,m2,m1,m0)
    out = np.ones((1, 1), complex)
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([U[a][b], U[b][c], Ud[d][c], Ud[a][d]]) for a, b, c, d in itertools.product(range(2), repeat=4))
HB = -(W + W.conj().T)
cas = 0.5 * (rl.casimir_L + rl.casimir_R)
c1 = np.real(np.diag(cas))[sec]
HE = sum(kron4([np.diag(c1) if l == k else np.eye(6) for l in range(4)]) for k in range(4)).real
HE = np.diag(HE).copy()
det = R(rl.det_U)
hD1 = det + det.conj().T
HD = sum(kron4([hD1 if l == k else np.eye(6) for l in range(4)]) for k in range(4))
codes = sorted(sum(s << (4 * l) for l, s in enumerate(cfg)) for cfg in itertools.product(sec, repeat=4))
print("electric coefficient (Casimir values on sector):", np.round(c1, 12), " HD hermitian:", np.abs(HD - HD.conj().T).max())

def ue(a): return np.diag(np.exp(-1j * a * HE))
def ub(b): return sla.expm(-1j * b * HB)
def ud(e): return sla.expm(-1j * e * HD)

def dense(kind, order, base, ents, th):
    M = np.zeros((1296, 1296), complex)
    for (i, j), lp in ents.items(): M[i, j] = lp.evaluate(*th)
    return M

rng = np.random.default_rng(434)
out = {"seed": 434, "rows": []}
for kind, order in [("UE", 1), ("UB", 1), ("UD", 1), ("step", 1), ("step", 2)]:
    base, ents = LC.exact_target(kind, order)
    worst = 0.0
    for trial in range(5):
        al, be, et = rng.uniform(0.05, 2.5, 3)
        if kind == "UD":
            th = (et / base[0], 0.0, 0.0); ref = ud(et)
        else:
            th = (al / base[0], be / base[1], np.sqrt(2) * be / base[2])
            ref = {("UE", 1): ue(al), ("UB", 1): ub(be), ("step", 1): ub(be) @ ue(al),
                   ("step", 2): ue(al / 2) @ ub(be) @ ue(al / 2)}[(kind, order)]
        M = dense(kind, order, base, ents, th)
        err = float(np.abs(M - ref).max())
        unit = float(np.abs(M.conj().T @ M - np.eye(1296)).max())
        worst = max(worst, err)
        out["rows"].append({"kind": kind, "order": order, "alpha": al, "beta": be, "eta": et, "max_abs_err": err, "unitarity_dev_of_exact": unit})
    print(kind, order, "base", base, "nnz", len(ents), "worst max|exact - expm|", worst)
    out[f"worst_{kind}_{order}"] = worst
# pins file vs recomputation
pins = LC.compute_pins()
txt = open(LC.PINS_FILE).read()
ok = all(p["sha256"] in txt for p in pins.values())
print("Pins3.lean contains all recomputed SHA:", ok)
out["pins_match_recompute"] = ok
out["pins"] = pins
# sensitivity: perturb the target text -> different sha
import copy
base, ents = LC.exact_target("step", 1)
sha0 = hashlib.sha256(LC.target_text(ents).encode()).hexdigest()
e2 = {k: LC.Laurent3(v) for k, v in ents.items()}
k0 = sorted(e2)[5]; lp = e2[k0]; ex = sorted(lp)[0]
variants = {}
v = {k: LC.Laurent3(vv) for k, vv in ents.items()}; v[k0] = LC.Laurent3(v[k0]); v[k0][ex] = v[k0][ex] * (-1); variants["sign flip"] = v
v = {k: LC.Laurent3(vv) for k, vv in ents.items()}; v[k0] = LC.Laurent3(v[k0]); old = v[k0][ex]; v[k0][ex] = old * LC.E.KNum.of(2); variants["coeff x2"] = v
v = {k: LC.Laurent3(vv) for k, vv in ents.items()}; v[k0] = v[k0].shift((0, 1, 0)); variants["exponent shift"] = v
v = {k: LC.Laurent3(vv) for k, vv in ents.items()}; del v[k0]; variants["entry dropped"] = v
out["sensitivity"] = {n: hashlib.sha256(LC.target_text(v).encode()).hexdigest() != sha0 for n, v in variants.items()}
print("sha sensitivity:", out["sensitivity"])
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/tester/434-target-check.json", "w"), indent=1)
