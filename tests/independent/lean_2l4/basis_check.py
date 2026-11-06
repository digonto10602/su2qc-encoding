import sys, time, json
from fractions import Fraction
import numpy as np
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.lean import exact as E, certify as C
from su2plaq.exact.physical import physical_basis
t0=time.time()
basis = E.exact_physical_basis("cg")
fb = physical_basis(convention="cg")
print("exact basis", len(basis), f"{time.time()-t0:.1f}s")
# max entry error myself
worst = 0
for st, fk, fa in zip(basis, fb.keys, fb.amps):
    o = np.argsort(fk)
    assert np.array_equal(st["keys"], fk[o])
    worst = max(worst, max(abs(k.to_complex()-a) for k,a in zip(st["amps"], fa[o])))
print("max |exact - float| basis entry:", worst)
# exact Gram: <psi_k|psi_l> = delta_kl
by_key = {}
for k, st in enumerate(basis):
    for key, a in zip(st["keys"].tolist(), st["amps"]):
        by_key.setdefault(key, []).append((k, a))
gram = {}
for key, lst in by_key.items():
    for k, a in lst:
        for l, b in lst:
            gram[(k,l)] = gram.get((k,l), E.KNum(0)) + a.conj()*b
off = [(kl, v) for kl, v in gram.items() if kl[0]!=kl[1] and not v.is_zero()]
dg = [kl for kl in range(433) if gram.get((kl,kl)) != E.KNum(1)]
print("exact Gram: nonzero off-diagonal:", len(off), " diagonal != 1:", len(dg))
# encoded states
from su2plaq.encodings.twelve import TwelveQubit
enc = TwelveQubit()
es = E.exact_encoded_states(enc)
bc = {}
for k, st in enumerate(es):
    for c, a in zip(st["codes"].tolist(), st["amps"]):
        bc.setdefault(c, []).append((k,a))
g2 = {}
for c, lst in bc.items():
    for k,a in lst:
        for l,b in lst:
            g2[(k,l)] = g2.get((k,l), E.KNum(0)) + a.conj()*b
print("encoded states: exact Gram off-diag nonzero:", sum(1 for (k,l),v in g2.items() if k!=l and not v.is_zero()), "diag != 1:", sum(1 for k in range(433) if g2.get((k,k)) != E.KNum(1)))
print("terms:", sum(len(s["codes"]) for s in es), " distinct codes", len(bc))
# H_B blocks
blocks = E._beta_blocks()
sizes = sorted(len(ks) for ks,_ in blocks)
from collections import Counter
print("H_B blocks:", len(blocks), "sizes histogram", dict(Counter(sizes)), "sum", sum(sizes))
# projector identities exactly
bad = 0
Hex = E.exact_HB()
for ks, proj in blocks:
    n = len(ks)
    lams = list(proj)
    # sum P = 1 ; sum lam P = H ; P^2 = P ; P_l P_m = 0
    S = [[E.KNum(0)]*n for _ in range(n)]
    HH = [[E.KNum(0)]*n for _ in range(n)]
    for lam in lams:
        P = proj[lam]
        for i in range(n):
            for j in range(n):
                S[i][j] = S[i][j] + P[i][j]
                HH[i][j] = HH[i][j] + P[i][j]*Fraction(lam)
    pos = {k:i for i,k in enumerate(ks)}
    for i in range(n):
        for j in range(n):
            if S[i][j] != (E.KNum(1) if i==j else E.KNum(0)): bad += 1
            h = Hex.get((ks[i], ks[j]), E.KNum(0))
            if HH[i][j] != h: bad += 1
    mm = E._matmul
    for lam in lams:
        P2 = mm(proj[lam], proj[lam])
        for i in range(n):
            for j in range(n):
                if P2[i][j] != proj[lam][i][j]: bad += 1
    for a_, b_ in [(lams[0], lams[1])] if len(lams)>1 else []:
        Z = mm(proj[a_], proj[b_])
        if any(not x.is_zero() for r in Z for x in r): bad += 1
print("projector identity violations:", bad)
# H hermitian & real? 
asym = sum(1 for (i,j),v in Hex.items() if Hex.get((j,i), E.KNum(0)).conj() != v)
print("H_B (exact) Hermiticity violations:", asym, "nnz", len(Hex))
# spectrum multiplicities: trace P_lambda summed
mult = Counter()
for ks, proj in blocks:
    for lam, P in proj.items():
        tr = E.KNum(0)
        for i in range(len(ks)): tr = tr + P[i][i]
        assert tr.is_real() and not (tr.c or tr.e or tr.g)
        mult[lam] += tr.a
print("spectrum multiplicities:", {str(k): str(v) for k,v in sorted(mult.items())})
