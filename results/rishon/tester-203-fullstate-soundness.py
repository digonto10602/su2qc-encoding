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
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.rishon import verify as Vf
from su2plaq.rishon.operators import inner_codes, inner_target
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.circuits.rishon import build_UE

SEED = 20261106
rng = np.random.default_rng(SEED)
LK, CORN = ind.LK, ind.CORN
G8, n8 = ind.end_gens(8)
M4 = [G8[a][0][np.ix_(range(4), range(4))] for a in range(3)]      # 4x4 end generators, basis = pair integer 0..3
ALPHA = 0.37
enc = RishonEncoding()

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

codes = inner_codes()
V = inner_target("UE", ALPHA, None, 1)

def full_error(qc, phase, label):
    """max over sample of || U Psi - phase (V (x) 1) Psi || with U applied by the sparse simulator on the full 48-bit keys"""
    worst = 0.0; worst_t = None
    for s in samples:
        keys, amps = s["keys"], s["amps"]
        batch = ss.run_batch(qc, keys, cap=5_000_000)
        out = {}
        for k, c, a in zip(batch.keys.tolist(), batch.cols.tolist(), batch.amps.tolist()):
            out[k] = out.get(k, 0) + a * amps[c]
        # target: apply V on inner index for each outer pattern
        inner = keys & 0xFFFF; outer = keys >> 16
        rows = np.searchsorted(codes, inner); assert (codes[rows] == inner).all()
        tgt = {}
        for o in np.unique(outer):
            m = outer == o
            vec = np.zeros(len(codes), complex); np.add.at(vec, rows[m], amps[m])
            w = phase * (V @ vec)
            for r in np.flatnonzero(np.abs(w) > 1e-16):
                kk = int(codes[r]) | (int(o) << 16)
                tgt[kk] = tgt.get(kk, 0) + w[r]
        allk = set(out) | set(tgt)
        err = np.sqrt(sum(abs(out.get(k, 0) - tgt.get(k, 0)) ** 2 for k in allk))
        if err > worst: worst, worst_t = err, s["types"]
    return worst, worst_t

def circ(extra=None, n_anc=7):
    qc = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(n_anc, "a"))
    qc.compose(build_UE(ALPHA), qubits=list(range(16)), inplace=True)
    if extra: extra(qc)
    return qc
aaaa = [0, 1, 4, 5, 8, 9, 12, 13]
def and_chain_phase(eps):
    def f(qc):
        anc = list(range(48, 55)); c = aaaa
        qc.ccx(c[0], c[1], anc[0])
        for i in range(1, 7): qc.ccx(anc[i - 1], c[i + 1], anc[i])
        qc.p(eps, anc[-1])
        for i in range(6, 0, -1): qc.ccx(anc[i - 1], c[i + 1], anc[i])
        qc.ccx(c[0], c[1], anc[0])
    return f
mutants = {
    "UE_correct": circ(),
    "phase_1e-3_only_on_inner_AAAA": circ(and_chain_phase(1e-3)),
    "phase_1e-6_only_on_inner_AAAA": circ(and_chain_phase(1e-6)),
    "ccz_valid_codes_(0,1,4)": circ(lambda q: q.ccz(0, 1, 4)),
    "link2_angle_off_by_1e-4": circ(lambda q: q.p(1e-4, 9)),   # p on L2 of link 2 -> phase on its quartet?? (bit 9 = R1 of link 2)
    "ccz_on_invalid_pattern_dontcare": circ(lambda q: q.ccz(0, 1, 2)),
}
res = {}
for name, qc in mutants.items():
    v = Vf.verify(qc, enc, "UE", ALPHA, None)
    t0 = time.time()
    fe, ft = full_error(qc, v.phase, name)
    res[name] = dict(verify_ok=v.ok, verify_reason=v.reason, verify_op_norm_error=v.op_norm_error, verify_block=v.block_error,
                     verify_leak=v.leak_amplitude, full_state_max_err=fe, worst_types=ft, sec=round(time.time() - t0, 1))
    print(name, res[name], flush=True)
out = dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), seed=SEED, alpha=ALPHA,
           n_states=len(samples), own_gauss_max_40=gmax, norm_dev=nrm, n_inner_AAAA_states=n_inner_pure["AAAA"],
           type_examples=[s["types"] for s in samples[:10]], mutants=res)
json.dump(out, open("results/rishon/tester-203-fullstate-soundness.json", "w"), indent=1, default=float)
