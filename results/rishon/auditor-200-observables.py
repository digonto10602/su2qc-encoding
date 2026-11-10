"""Auditor 200: independent closed-sector recomputation of the rishon/KS observables (no project imports)."""
import json, numpy as np
from scipy.linalg import expm
obs = json.load(open("results/rishon/observables.json"))
def run(alpha, beta, theory):
    if theory == "rishon":
        HE = np.diag([0, 3, 0.]); HB = -4*np.array([[0,1,0],[1,0,1],[0,1,0.]]); psi0 = np.array([1,0,0],complex)
    else:
        HE = np.diag([0, 3.]); HB = -2*np.array([[0,1],[1,0.]]); psi0 = np.array([1,0],complex)
    U = expm(-1j*beta*HB) @ expm(-1j*alpha*HE)
    out = {}; psi = psi0
    for n in (1, 2):
        psi = U @ psi
        out[n] = dict(E_link=float(np.real(psi.conj()@HE@psi))/4, P=float(-0.5*np.real(psi.conj()@HB@psi)), echo=float(abs(psi[0])**2))
    return out
dev = 0.0; rows = []
for th in ("rishon", "ks"):
    for r in obs[th]:
        mine = run(r["alpha"], r["beta"], th)[r["n"]]
        d = max(abs(mine[k]-r[k]) for k in mine); dev = max(dev, d)
        rows.append((th, r["alpha"], r["beta"], r["n"], {k: round(r[k], 6) for k in mine}, d))
for x in rows: print(x)
print("max deviation", dev)
