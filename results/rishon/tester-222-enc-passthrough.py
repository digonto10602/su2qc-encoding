"""Tester 222 D2: RishonEncoding.target(..., eta=) vs an own contraction <psi_k'|(V (x) 1_outer)|psi_k> with V built independently (own JW, own expm).
Uses production only for the physical basis (keys, amps) and the encoding call under test."""
import json, subprocess, itertools
import numpy as np
SECTOR = [3, 5, 6, 9, 10, 12]
def c_op(k):
    M = np.zeros((16, 16))
    for n in range(16):
        if (n >> k) & 1: M[n ^ (1 << k), n] = (-1) ** sum((n >> m) & 1 for m in range(k))
    return M
c = [c_op(k) for k in range(4)]; cd = [m.T for m in c]
U = lambda i, j: c[i] @ cd[2 + j]; res = lambda M: M[np.ix_(SECTOR, SECTOR)]
Ub = [[res(U(i, j)) for j in range(2)] for i in range(2)]; Ud = [[Ub[i][j].T for j in range(2)] for i in range(2)]
det = res(U(0, 0) @ U(1, 1) - U(0, 1) @ U(1, 0))
def kron4(ms):
    out = np.ones((1, 1))
    for m in ms: out = np.kron(m, out)
    return out
W = sum(kron4([Ub[a][b], Ub[b][cc], Ud[d][cc], Ud[a][d]]) for a, b, cc, d in itertools.product(range(2), repeat=4))
HB = -(W + W.T)
HD = sum(kron4([(det + det.T) if l == k else np.eye(6) for l in range(4)]) for k in range(4))
cas = np.array([0, .75, .75, .75, .75, 0.]); HE = np.array([sum(cas[(i // 6 ** l) % 6] for l in range(4)) for i in range(1296)])
def fn(H):
    w, V = np.linalg.eigh(H); return lambda x: (V * np.exp(-1j * x * w)) @ V.T
UBf, UDf = fn(HB), fn(HD)
UEf = lambda a: np.diag(np.exp(-1j * a * HE))
from su2plaq.encodings.rishon import RishonEncoding
enc = RishonEncoding(); b = enc.basis
codes = np.array(sorted(sum(s << (4 * l) for l, s in enumerate(t)) for t in itertools.product(SECTOR, repeat=4)))
# sorted inner codes == row-major order of kron(link3..link0) with sorted sector: index = sum s_l 6^l
pos = {int(cd_): i for i, cd_ in enumerate(codes)}
from su2plaq.rishon.operators import inner_codes
assert np.array_equal(inner_codes(), codes)
rng = np.random.default_rng(20261110)
from su2plaq.rishon.physical import closed_indices
states = [int(x) for x in closed_indices(b)[:17]] + [int(x) for x in rng.choice(len(b.keys), 15, replace=False)]
def contract(V):
    n = len(states); out = np.zeros((n, n), complex)
    comps = []
    for k in states:
        keys = np.asarray(b.keys[k], dtype=np.int64); amps = np.asarray(b.amps[k], dtype=np.complex128)
        d = {}
        for key, a in zip(keys, amps):
            o = int(key) >> 16; i = pos[int(key) & 0xFFFF]
            d.setdefault(o, np.zeros(1296, complex))[i] += a
        comps.append(d)
    for i, dk in enumerate(comps):
        for j, dl in enumerate(comps):
            s = 0
            for o, z in dl.items():
                if o in dk: s += np.vdot(dk[o], V @ z)
            out[i, j] = s
    return out
res_ = {}
for (a, bb, e) in ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53)):
    for kind, order, V in (("UD", 1, UDf(e)), ("step", 1, UBf(bb) @ UDf(e) @ UEf(a)),
                           ("step", 2, UEf(a / 2) @ UDf(e / 2) @ UBf(bb) @ UDf(e / 2) @ UEf(a / 2))):
        mine = contract(V)
        got = enc.target(kind, a, bb, order, states=states, eta=e)
        res_[f"{kind}-o{order}-{(a, bb, e)}"] = float(np.abs(mine - got).max())
        res_[f"{kind}-o{order}-{(a, bb, e)}-unit_diag_dev"] = float(np.abs(np.abs(np.diag(mine))).max())
# eta=None: unchanged vs the previous two-layer target (via own)
got = enc.target("step", 0.37, 0.61, 1, states=states); mine = contract(UBf(0.61) @ UEf(0.37))
res_["step-two-layer-eta-None"] = float(np.abs(got - mine).max())
# enc.inner_target pass-through
res_["enc.inner_target(step, eta) vs own"] = float(np.abs(enc.inner_target("step", 0.37, 0.61, 1, eta=0.29) - UBf(0.61) @ UDf(0.29) @ UEf(0.37)).max())
res_["n_states"] = len(states)
res_["git"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
json.dump(res_, open("results/rishon/tester-222-enc-passthrough.json", "w"), indent=1)
print(json.dumps(res_, indent=1))
