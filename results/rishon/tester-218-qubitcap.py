"""Tester 218: is there a hard 62-qubit limit in the sparse engine, where does it come from, and can any valid circuit with 63..80 qubits be evaluated?
Pads the F5 round-1 circuit (51 qubits, valid) with k extra ancillas: (a) idle, (b) live (CX(q0->a); ... ; CX(q0->a) compute/uncompute, still the same unitary),
and calls (1) sparse_sim.run_batch directly, (2) rishon.compress.evaluate.evaluate_circuit (production verdict, trial+full), (3) rishon verify with engine='aer_mps'."""
import sys, os, json, time, importlib.util, traceback
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
def imp(n, f):
    sp = importlib.util.spec_from_file_location(n, os.path.join(here, f)); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = imp("c218", "tester-218-common.py")
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress import evaluate as RE
from su2plaq.compress import evaluate as LE
from su2plaq.evaluate import sparse_sim as ss
s = rishon_spec('step')
res = {}
def padded(cid, extra, live):
    mod = LE.load_program(C.program_path(cid))
    b = mod.build(s)
    a = b.alloc(extra, "pad") if extra else []
    if live:
        for q in a: b.cx(0, q)
        for q in reversed(a): b.cx(0, q)
    return b.circuit()
for cid in ("r01-F5-001",):
    for extra, live in ((14, False), (14, True), (15, False), (15, True), (16, True), (17, True), (29, True)):
        qc = padded(cid, extra, live)
        n = qc.num_qubits
        row = dict(cid=cid, extra=extra, live=live, n_qubits=n)
        # (1) run_batch directly
        try:
            ss.run_batch(qc, np.array([0, 1], dtype=np.int64)); row['run_batch'] = 'ok'
        except Exception as e:
            row['run_batch'] = f"{type(e).__name__}: {e}"
        # (2) production verdict
        t0 = time.time()
        try:
            r = RE.evaluate_circuit(qc, s, 'trial')
            row['evaluate_trial'] = dict(valid=r.valid, reason=r.reason, message=r.message)
        except Exception as e:
            row['evaluate_trial'] = f"EXCEPTION {type(e).__name__}: {e}"
        # (3) aer_mps engine
        try:
            from su2plaq.rishon import verify as RV
            from su2plaq.compress import oracle
            enc = RE.get_encoding(s.encoding).encoding
            V = oracle.target(s)
            rv = RV.verify(qc, enc, s.kind, s.alpha, s.beta, s.order, tol_err=s.tol_err, tol_gauss=s.tol_gauss, gauss=False, engine='aer_mps', cap=s.support_cap, target=V,
                           states=RE.trial_states(s))
            row['verify_aer_mps_trial'] = dict(ok=rv.ok, reason=rv.reason, engine=rv.engine, op_norm_error=rv.op_norm_error, certified=rv.certified)
        except Exception as e:
            row['verify_aer_mps_trial'] = f"EXCEPTION {type(e).__name__}: {str(e)[:200]}"
        row['seconds'] = time.time() - t0
        print(json.dumps(row, default=str), flush=True)
        res[f"{cid}+{extra}{'live' if live else 'idle'}"] = row
json.dump(res, open(os.path.join(here, 'tester-218-qubitcap.json'), 'w'), indent=1, default=str)
