"""Tester step 1.6: paulo_circuit() counts from the QPY; with_outer embedding (outer idle); evaluate vs target UB(beta=1).
Usage: PYTHONPATH=src python check_paulo_outer.py out.json"""
import sys, json, time, subprocess, warnings
import numpy as np
warnings.filterwarnings("ignore")
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import paulo_circuit
from su2plaq.evaluate.evaluator import evaluate

enc = TwelveQubit()
out = dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted")
V = enc.target("UB", None, 1.0)
tol = dict(tol_err=2e-5, tol_gauss=2e-5)
res = {}
for outer in (False, True):
    qc = paulo_circuit(with_outer=outer)
    ops = qc.count_ops()
    info = dict(qubits=qc.num_qubits, cx=ops["cx"], T=ops.get("t", 0) + ops.get("tdg", 0), regs=[(r.name, len(r)) for r in qc.qregs], gates=dict(ops),
                depth=qc.depth(), global_phase=float(qc.global_phase))
    used = sorted({qc.find_bit(q).index for i in qc.data for q in i.qubits})
    info["used_qubits_n"] = len(used); info["outer_touched"] = [u for u in used if 12 <= u < 28]
    t0 = time.time(); v = evaluate(qc, enc, V, engine="auto", **tol); dt = time.time() - t0
    info["verdict"] = dict(ok=v.ok, certified=v.certified, engine=v.engine, method=v.method, op_norm_error=v.op_norm_error, block=v.block_error, leak=v.leak_amplitude,
                           gauss=v.gauss_residual, max_leak=v.max_leak, dirty=v.dirty_ancilla, outer_bits_read=v.outer_bits_read, n_blocks=v.n_blocks, tolerances=v.tolerances, sec=dt)
    v2 = evaluate(qc, enc, V.conj().T, engine=v.engine, **tol)
    info["inverse_target"] = dict(ok=v2.ok, op_norm_error=v2.op_norm_error)
    res["with_outer" if outer else "plain"] = info
    print(outer, info["qubits"], info["cx"], info["T"], info["outer_touched"], info["verdict"], info["inverse_target"], flush=True)
out["res"] = res
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
