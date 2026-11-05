"""Tester step 1.3: peak stored amplitudes per input in the sparse engine, program order vs DAG order, exact vs synthesised U_B(0.61).
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_sparse_peak.py out.json"""
import sys, json, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_UB
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.metrics.cliffordt import synthesize

enc = TwelveQubit(); codes = enc.inner_codes(); pick = codes[[0, 7, 100, 311, 624]]
peak = [0]; orig = ss._coalesce
def spy(keys, cols, amps, n_qubits, n_cols, dropped):
    r = orig(keys, cols, amps, n_qubits, n_cols, dropped); peak[0] = max(peak[0], len(r[0])); return r
ss._coalesce = spy
res = []
def trial(name, qc):
    ops, ph = ss._translate(qc)
    for oname, order in (("program", range(len(ops))), ("dag", ss._schedule(ops))):
        peak[0] = 0; t0 = time.time()
        try:
            b = ss._run(ops, ph, qc.num_qubits, pick.astype(np.int64), 300_000_000, order); st = "ok"
        except ss.SimCapExceeded: st = "cap 3e8 exceeded"
        r = dict(circuit=name, order=oname, n_ops=len(ops), n_inputs=len(pick), peak_total=peak[0], peak_per_input=peak[0] / len(pick), status=st, seconds=time.time() - t0)
        res.append(r); print(r, flush=True)
qc = build_UB(0.61); trial("exact build_UB(0.61)", qc)
for eps in (1e-4, 1e-6):
    s, _ = synthesize(qc, eps); trial(f"synth eps={eps:g}", s)
json.dump(res, open(sys.argv[1], "w"), indent=1)
