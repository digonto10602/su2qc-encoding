"""Tester 203, item 2(a): is checking an outer-blind circuit on the 1296 inner codes enough for full physical states?
Own construction of random physical states (no su2plaq.rishon.physical): per type pattern, per corner Gauss kernel from own JW
end generators (tester-201 module), tensor product, random complex kernel combination.  Then apply mutated 48-qubit circuits
with the sparse simulator on the FULL 48-bit keys of each state and compare with (V_in (x) 1) Psi (V_in from production inner_target;
the production inner_target was verified against own expm in report 202)."""
import importlib.util, itertools, json, subprocess, sys, time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("ind", "results/rishon/tester-201-independent-counts.py")
ind = importlib.util.module_from_spec(spec); spec.loader.exec_module(ind)






SEED = 433
rng = np.random.default_rng(SEED)
LK, CORN = ind.LK, ind.CORN
G8, n8 = ind.end_gens(8)
M4 = [G8[a][0][np.ix_(range(4), range(4))] for a in range(3)]      # 4x4 end generators, basis = pair integer 0..3



def end_allowed(link, side, typ):
    """allowed pair integer values at an end, by link type (A: L full R empty; B: L empty R full; Q: single colour)"""
    full, empty, single = [3], [0], [1, 2]
    if typ == "A": return full if side == "L" else empty
    if typ == "B": return empty if side == "L" else full
    return single
def far_value(link, typ, near_side):
    far_side = "R" if near_side == "L" else "L"
    return end_allowed(link, far_side, typ)[0]   # A/B fixed; Q -> colour 1 (value 1)

def corner_kernel(c, types):
    ends = CORN[c]
    allowed = [end_allowed(l, s, types[l]) for l, s in ends]
    dims = [len(a) for a in allowed]
    idx = list(itertools.product(*[range(d) for d in dims]))
    pos = {t: i for i, t in enumerate(idx)}
    N = len(idx)
    Gt = []
    for a in range(3):
        Ga = np.zeros((N, N), complex)
        for t in idx:
            for e in range(4):
                v = allowed[e][t[e]]
                for ip, vp in enumerate(allowed[e]):
                    m = M4[a][vp, v]
                    if abs(m) > 1e-14:
                        t2 = list(t); t2[e] = ip
                        Ga[pos[tuple(t2)], pos[t]] += m
        # invariance check: M4 must not leave the allowed set
        for t in idx:
            for e in range(4):
                v = allowed[e][t[e]]
                col = M4[a][:, v]
                out = {vv for vv in range(4) if abs(col[vv]) > 1e-14}
                assert out <= set(allowed[e]), (types, c, e)
        Gt.append(Ga)
    C = sum(g @ g for g in Gt)
    w, U = np.linalg.eigh((C + C.conj().T) / 2)
    ker = U[:, w < 1e-9]
    return idx, allowed, ker

def build_state(types):
    ks = [corner_kernel(c, types) for c in range(4)]
    if any(k[2].shape[1] == 0 for k in ks): return None
    coef = [(rng.normal(size=k[2].shape[1]) + 1j * rng.normal(size=k[2].shape[1])) for k in ks]
    vec = [k[2] @ cf for k, cf in zip(ks, coef)]
    vec = [v / np.linalg.norm(v) for v in vec]
    # far ends of the outer links
    fixed = 0
    for l in range(4, 12):
        cs, ce, _ = LK[l]
        near_side = "L" if cs is not None else "R"
        fs = "R" if near_side == "L" else "L"
        fixed |= far_value(l, types[l], near_side) << (4 * l + (0 if fs == "L" else 2))
    keys = np.array([fixed], dtype=np.int64); amps = np.array([1.0 + 0j])
    for c in range(4):
        idx, allowed, _ = ks[c]
        ck = []; ca = []
        for i, t in enumerate(idx):
            if abs(vec[c][i]) < 1e-15: continue
            k = 0
            for e, (l, s) in enumerate(CORN[c]):
                k |= allowed[e][t[e]] << (4 * l + (0 if s == "L" else 2))
            ck.append(k); ca.append(vec[c][i])
        ck = np.array(ck, dtype=np.int64); ca = np.array(ca)
        keys = (keys[:, None] | ck[None, :]).ravel(); amps = (amps[:, None] * ca[None, :]).ravel()
    return keys, amps

def own_gauss(keys, amps):
    worst = 0.0
    for c in range(4):
        for a in range(3):
            out = {}
            for (l, s) in CORN[c]:
                q0 = 4 * l + (0 if s == "L" else 2)
                sub = (keys >> q0) & 3; base = keys & ~(np.int64(3) << q0)
                for r in range(4):
                    cf = M4[a][r][sub]; nz = np.abs(cf) > 1e-15
                    for kk, aa in zip(base[nz] | (np.int64(r) << q0), amps[nz] * cf[nz]):
                        out[int(kk)] = out.get(int(kk), 0) + aa
            worst = max(worst, np.sqrt(sum(abs(x) ** 2 for x in out.values())))
    return worst

# ---- sample of physical states (random type patterns with admissible kernels; plus forced inner AAAA / all-Q)
samples = []
tries = 0
want_inner = [("A",) * 4, ("Q",) * 4, ("A", "A", "B", "B")] + [tuple(rng.choice(list("ABQ"), 4)) for _ in range(5)]
t0 = time.time()
while len(samples) < 72 and tries < 4000:
    tries += 1
    inn = want_inner[len(samples) % len(want_inner)] if rng.random() < 0.5 else tuple(rng.choice(list("ABQ"), 4))
    out = tuple(rng.choice(list("ABQ"), 8))
    types = list(inn) + list(out)
    if sum(t == "Q" for t in types[:4]) + sum(t == "Q" for t in types[4:]) > 7: continue   # keep key counts small
    st = build_state(types)
    if st is None: continue
    keys, amps = st
    samples.append(dict(types="".join(types), keys=keys, amps=amps))
print("states built", len(samples), "tries", tries, f"{time.time()-t0:.1f}s", flush=True)
gmax = max(own_gauss(s["keys"], s["amps"]) for s in samples[:40])
nrm = max(abs(np.linalg.norm(s["amps"]) - 1) for s in samples)
print("own Gauss residual (40 states)", gmax, "norm dev", nrm)
n_inner_pure = {"AAAA": sum(s["types"][:4] == "AAAA" for s in samples)}


# ================= tester 433 part: output = (M (x) 1) Psi with M the block of MY sparse engine (outer qubits are spectators: checked, not touched)
import os, hashlib
here = os.path.join("results", "tester", "433")
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = imp("c433", "433-common.py"); eng = C.load_engine()
from su2plaq.rishon.compress.spec import rishon_spec
s0 = rishon_spec("step")
res = {}
for cid, fam in C.CANDS:
    for (a, b) in [(s0.alpha, s0.beta), (0.91, 0.23), (1.7, 1.0)]:
        T = eng.algebra_targets(a, b)
        codes = np.asarray(T["codes"]); V = T["step"]
        qc = C.build_circuit(cid, s0.with_angles(a, b))
        ops = eng.lower(qc); qs = eng.used_qubits(ops)
        assert not [q for q in qs if 16 <= q < 48], "outer qubit touched"
        sim = eng.Sim(codes, qs, thr=1e-15); sim.run(ops)
        M, wd, wo = sim.block(codes, list(range(16)))
        ph, e2, _ = eng.compare(M, V)
        worst_err = worst_gauss_out = worst_gauss_tgt = 0.0
        for st in samples:
            keys, amps = st["keys"], st["amps"]
            inner = keys & 0xFFFF; outer = keys >> 16
            rows = np.searchsorted(codes, inner); assert (codes[rows] == inner).all()
            out = {}; tgt = {}
            for o in np.unique(outer):
                m = outer == o
                vec = np.zeros(len(codes), complex); np.add.at(vec, rows[m], amps[m])
                wv = M @ vec; tv = ph * (V @ vec)
                for r in np.flatnonzero(np.abs(wv) > 1e-17): out[int(codes[r]) | (int(o) << 16)] = wv[r]
                for r in np.flatnonzero(np.abs(tv) > 1e-17): tgt[int(codes[r]) | (int(o) << 16)] = tv[r]
            allk = set(out) | set(tgt)
            err = float(np.sqrt(sum(abs(out.get(k, 0) - tgt.get(k, 0)) ** 2 for k in allk)))
            worst_err = max(worst_err, err)
            ko = np.array(list(out), dtype=np.int64); ao = np.array([out[k] for k in out])
            worst_gauss_out = max(worst_gauss_out, own_gauss(ko, ao))
        key = f"{cid}@{a},{b}"
        res[key] = dict(block_err=e2, n_states=len(samples), worst_full_state_err=worst_err, worst_own_gauss_residual_output=worst_gauss_out, leak=float(np.sqrt((wd + wo).max())))
        print(key, res[key], flush=True)
gin = max(own_gauss(s["keys"], s["amps"]) for s in samples)
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), seed=SEED, n_states=len(samples), own_gauss_input_max=gin,
               norm_dev=nrm, type_examples=[s["types"] for s in samples[:10]], rows=res), open(os.path.join(here, "433-physical.json"), "w"), indent=1, default=float)
print("input Gauss max", gin)
