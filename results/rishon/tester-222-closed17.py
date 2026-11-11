"""Tester 222: 17x17 closed block with det term, own construction (JW link algebra -> 1296-dim ops -> projection on the 16 vacua {A,B}^4 + loop)
vs the plan's closed formula (prompts/204 sec 2.5) vs production closed_block_full(g2, lam_d).  Run: PYTHONPATH=src python this."""
import itertools, json, subprocess, sys
import numpy as np
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1:
            M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
U = lambda i, j: c[i] @ cd[2 + j]
res = lambda M: M[np.ix_(SECTOR, SECTOR)]
Ub = [[res(U(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Ub[i][j].T for j in range(2)] for i in range(2)]
det = res(U(0, 0) @ U(1, 1) - U(0, 1) @ U(1, 0))
def kron4(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]]) for a, b, cc, d in itertools.product(range(2), repeat=4))
HB = -(W + W.T)
HD = sum(kron4([(det + det.T) if l == k else np.eye(6) for l in range(4)]) for k in range(4))
cas = np.array([0, .75, .75, .75, .75, 0.])
HE = np.array([sum(cas[(i // 6 ** l) % 6] for l in range(4)) for i in range(1296)])
# vacua {A,B}^4: A = sector idx 0, B = sector idx 5 ; bit_l = 1 if link l is B
vac_idx = [sum((5 if bits[l] else 0) * 6 ** l for l in range(4)) for bits in itertools.product((0, 1), repeat=4)]   # bits tuple (b0..b3), b0 = link b
vacs = np.zeros((1296, 17)); 
for n, i in enumerate(vac_idx): vacs[i, n] = 1
idxA = 0 + 0 + 5 * 36 + 5 * 216      # b,r = A ; t,l = B
vacA = np.zeros(1296); vacA[idxA] = 1
loop = -(HB @ vacA) / 4.0
loop /= np.linalg.norm(loop)
vacs[:, 16] = loop
out = {"basis_orth_dev": float(np.abs(vacs.T @ vacs - np.eye(17)).max())}
sys_ = {}
sys.path.insert(0, "src")
from su2plaq.rishon import operators as ops
for g2 in (0.5, 1.0, 2.0):
    for lam in (0.0, 0.2, 0.5, -0.5):
        H = g2 / 2 * np.diag(HE) + HB / g2 + lam * HD
        Hb = vacs.T @ H @ vacs
        inv = float(np.abs(H @ vacs - vacs @ Hb).max())                  # invariance of the 17-dim span
        # plan formula
        Hf = np.zeros((17, 17))
        Hf[16, 16] = g2 / 2 * 3
        for n, bits in enumerate(itertools.product((0, 1), repeat=4)):
            pass
        # vacua index in vacs: n = position in product((0,1),repeat=4) (b0 slowest); the loop couples to vacA and vacB = inner types B,B,A,A
        nA = [n for n, bits in enumerate(itertools.product((0, 1), repeat=4)) if bits == (0, 0, 1, 1)][0]
        nB = [n for n, bits in enumerate(itertools.product((0, 1), repeat=4)) if bits == (1, 1, 0, 0)][0]
        Hf[16, nA] = Hf[nA, 16] = Hf[16, nB] = Hf[nB, 16] = -4 / g2
        for n, bits in enumerate(itertools.product((0, 1), repeat=4)):
            for l in range(4):
                b2 = list(bits); b2[l] ^= 1
                m = list(itertools.product((0, 1), repeat=4)).index(tuple(b2))
                Hf[n, m] += 2 * lam
        formula_dev = float(np.abs(Hf - Hb).max())
        pv = ops.closed_block_full(g2, lam)
        ev_own = np.sort(np.linalg.eigvalsh(Hb)); ev_prod = np.sort(np.linalg.eigvalsh(pv))
        sys_[f"g2={g2},lam={lam}"] = {"span_invariance_dev": inv, "own_block_vs_plan_formula": formula_dev,
                                      "eig_own_vs_production": float(np.abs(ev_own - ev_prod).max()),
                                      "entrywise_prod_vs_own_block": float(np.abs(pv - Hb).max()),
                                      "n_zero_levels": int(np.sum(np.abs(ev_own) < 1e-9)), "hermitian_prod": float(np.abs(pv - pv.conj().T).max())}
out["blocks"] = sys_
out["git"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
json.dump(out, open("results/rishon/tester-222-closed17.json", "w"), indent=1)
print(json.dumps(out, indent=1))
