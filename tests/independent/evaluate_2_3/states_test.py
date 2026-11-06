"""states= subset vs full evaluation: independent dense computation for a diagonal circuit (UE + random diagonal perturbation)."""
import json, numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from su2plaq.circuits import twelve as C
from su2plaq.compress import oracle
from su2plaq.compress.spec import default_spec, get_encoding
from su2plaq.evaluate import evaluator as ev
spec = default_spec("twelve", "UE"); enc = get_encoding("twelve")
V = oracle.target(spec)
eb = enc.physical_vectors()
rng = np.random.default_rng(20261105)
qc = C.build_UE(spec.alpha, with_outer=True)
# diagonal perturbation: p(theta_q) on a few data+outer qubits and cp between pairs
th = {int(q): float(rng.normal() * 3e-3) for q in rng.choice(28, 5, replace=False)}
cps = [(int(a), int(b), float(rng.normal() * 3e-3)) for a, b in (rng.choice(28, 2, replace=False) for _ in range(4))]
for q, t in th.items(): qc.p(t, q)
for a, b, t in cps: qc.cp(t, a, b)
# independent diagonal d(c) for the whole circuit = exp(i * sum phases) * global; compute from the UE core separately:
# A = sum_c conj(psi_k'[c]) d(c) psi_k[c]; need d(c) for the full circuit: use a Z-basis phase function from the gates
def phase_fn(codes):
    ph = np.zeros(len(codes))
    for inst in qc.data:
        n = inst.operation.name; qs = [qc.find_bit(q).index for q in inst.qubits]; pr = [float(x) for x in inst.operation.params]
        bit = lambda q: ((codes >> q) & 1).astype(float)
        if n == "p": ph += pr[0] * bit(qs[0])
        elif n == "cp": ph += pr[0] * bit(qs[0]) * bit(qs[1])
        elif n == "rz": ph += pr[0] * (bit(qs[0]) - 0.5)
        else: raise RuntimeError(n)
    return ph + float(qc.global_phase)
print({i.operation.name for i in qc.data})
dim = 433
A = np.zeros((dim, dim), complex)
# gather unique codes
allc = np.unique(np.concatenate(eb.codes))
idx = {int(c): i for i, c in enumerate(allc)}
dvals = np.exp(1j * phase_fn(allc))
import scipy.sparse as sp
rows, cols, vals = [], [], []
for k in range(dim):
    rows += [idx[int(c)] for c in eb.codes[k]]; cols += [k] * len(eb.codes[k]); vals += list(eb.amps[k])
Psi = sp.csr_matrix((vals, (rows, cols)), shape=(len(allc), dim))
A = (Psi.conj().T @ sp.diags(dvals) @ Psi).toarray()
def ref(cols_):
    cols_ = np.asarray(cols_); Ac = A[:, cols_]; Vc = V[:, cols_]
    tr = np.vdot(Vc, Ac); ph = tr / abs(tr)
    return float(np.linalg.norm(Ac - ph * Vc, 2))
res = {}
full = ev.evaluate(qc, enc, V, tol_err=1e-2, tol_gauss=1e-2, method="physical")
res["full"] = dict(ref=ref(np.arange(dim)), got=full.block_error, leak=full.leak_amplitude, n=full.n_inputs, gauss=full.gauss_residual)
subs = {"first5": [0, 1, 2, 3, 4], "rand64_s0": np.sort(np.random.default_rng(0).choice(dim, 64, replace=False)),
        "rand10_s7": np.sort(np.random.default_rng(7).choice(dim, 10, replace=False)), "single_200": [200], "dup_unsorted": [300, 5, 5, 99], "last": [432], "all": np.arange(dim)}
worst = 0
for nm, s in subs.items():
    v = ev.evaluate(qc, enc, V, tol_err=1e-2, tol_gauss=1e-2, states=s)
    r = ref(np.unique(s)); d = abs(r - v.block_error)
    res[nm] = dict(n=v.n_inputs, ref=r, got=v.block_error, absdiff=d, leak=v.leak_amplitude)
    worst = max(worst, d)
    print(nm, res[nm])
res["max_abs_diff"] = worst
# validity: bad inputs
for bad in ([], [-1], [433], [0.5]):
    try:
        ev.evaluate(qc, enc, V, states=bad); res[f"bad_{bad}"] = "accepted"
    except Exception as e: res[f"bad_{bad}"] = type(e).__name__
print(res["full"], worst, {k: v for k, v in res.items() if k.startswith("bad")})
json.dump(res, open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv/states.json", "w"), indent=1, default=float)
