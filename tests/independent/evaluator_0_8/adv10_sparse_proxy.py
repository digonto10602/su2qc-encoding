"""Proxy for M1-T1: does the sparse engine stay under its 5e6-amplitude cap on a circuit with 14 gridsynth words (eps=1e-6)?"""
from common import *
import mpmath
from pygridsynth.gridsynth import gridsynth_gates
from su2plaq.evaluate import sparse_sim as ss
mpmath.mp.dps = 40
rng = np.random.default_rng(20261104)
def word(qc, q, theta, eps=1e-6):
    s = gridsynth_gates(mpmath.mpf(repr(theta)), mpmath.mpf(repr(eps)))
    for ch in reversed(s):       # letters act right to left
        {"H": qc.h, "T": qc.t, "S": qc.s, "X": qc.x}.get(ch, lambda q: None)(q)
codes = enc.inner_codes()
def run(nanc_words, n_rot=14):
    qc = QuantumCircuit(12 + nanc_words)
    for i in range(n_rot):
        a, b = rng.choice(12, 2, replace=False); t = 12 + (i % nanc_words)
        qc.ccx(a, b, t); qc.h(t); word(qc, t, float(rng.uniform(0.1, 3)))
        qc.h(t)
        qc.ccx(a, b, t)
    t0 = time.time()
    try:
        b = ss.run_batch(qc, codes, cap=5_000_000); n = len(b.keys); st = "ok"
    except ss.SimCapExceeded as e: n = None; st = "CAP EXCEEDED"
    return st, n, time.time() - t0, qc.size()
for na in (3, 4, 14):
    st, n, t, sz = run(na)
    print(f"14 words on {na} ancilla qubit(s): {st}, stored amplitudes at end {n}, gates {sz}, {t:.1f}s", flush=True)
